import AVFoundation
import AudioToolbox
import Combine
import Foundation

@MainActor final class ProbeController: ObservableObject {
    @Published var status = "Ready. No microphone capture has started."
    @Published var reading = "Direction unknown"
    @Published var running = false
    private var engine: SpatialProbeEngine?
    private var generation = 0

    func start() {
        guard !running else { return }
        generation += 1
        let version = generation
        running = true
        status = "Requesting microphone permission…"
        Task { [self] in
            let allowed = await AVCaptureDevice.requestAccess(for: .audio)
            guard version == generation else { return }
            guard allowed else { running = false; status = "Microphone access denied."; return }
            let next = SpatialProbeEngine { [weak self] status, reading in
                Task { @MainActor in
                    guard let self, self.generation == version else { return }
                    self.status = status; self.reading = reading
                }
            }
            engine = next
            next.start()
            // A bounded probe, not a background recorder. No samples are saved or uploaded.
            try? await Task.sleep(for: .seconds(8))
            if generation == version { stop() }
        }
    }
    func stop() {
        guard running || engine != nil else { return }
        let lastStatus = status
        generation += 1
        engine?.stop(); engine = nil; running = false
        status = "Stopped. No audio saved or uploaded. Last input: \(lastStatus)"
        reading = "Direction unknown · microphone off"
    }
}

private final class SpatialProbeEngine: NSObject, AVCaptureAudioDataOutputSampleBufferDelegate, @unchecked Sendable {
    private let session = AVCaptureSession()
    private let queue = DispatchQueue(label: "aware.spatial.probe")
    private let update: @Sendable (String, String) -> Void
    private var lastUpdate = 0.0
    private var frames: [Float] = []
    init(update: @escaping @Sendable (String, String) -> Void) { self.update = update }
    func start() { queue.async { self.configure() } }
    func stop() { queue.async { if self.session.isRunning { self.session.stopRunning() }; self.frames = [] } }
    private func configure() {
        do {
            guard let device = AVCaptureDevice.default(for: .audio) else { throw ProbeError.message("No microphone") }
            let input = try AVCaptureDeviceInput(device: device)
            session.beginConfiguration()
            guard session.canAddInput(input) else { session.commitConfiguration(); throw ProbeError.message("Cannot add microphone") }
            session.addInput(input)
            guard input.isMultichannelAudioModeSupported(.firstOrderAmbisonics) else {
                session.commitConfiguration()
                throw ProbeError.message("This route does not support first-order spatial capture. Try the newer iPhone with built-in mics, no headset.")
            }
            input.multichannelAudioMode = .firstOrderAmbisonics
            let output = AVCaptureAudioDataOutput()
            output.spatialAudioChannelLayoutTag = kAudioChannelLayoutTag_HOA_ACN_SN3D | 4
            guard session.canAddOutput(output) else { session.commitConfiguration(); throw ProbeError.message("Cannot add spatial output") }
            session.addOutput(output)
            output.setSampleBufferDelegate(self, queue: queue)
            session.commitConfiguration()
            session.startRunning()
            update("Listening for 8 seconds · FOA requested", "Verifying four-channel buffers…")
        } catch { update("Capture unavailable: \(error.localizedDescription)", "Direction unknown") }
    }
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let format = CMSampleBufferGetFormatDescription(sampleBuffer),
              let asbd = CMAudioFormatDescriptionGetStreamBasicDescription(format)?.pointee,
              asbd.mChannelsPerFrame == 4,
              asbd.mFormatID == kAudioFormatLinearPCM,
              asbd.mBitsPerChannel == 32,
              asbd.mFormatFlags & kAudioFormatFlagIsFloat != 0,
              asbd.mFormatFlags & kAudioFormatFlagIsBigEndian == 0,
              let layout = CMAudioFormatDescriptionGetChannelLayout(format, sizeOut: nil),
              layout.pointee.mChannelLayoutTag == (kAudioChannelLayoutTag_HOA_ACN_SN3D | 4) else {
            update("Unexpected sample format; refusing to guess channel order", "Direction unknown"); return
        }
        guard let values = Self.readFloats(sampleBuffer) else {
            update("Could not decode native audio buffers", "Direction unknown"); return
        }
        frames.append(contentsOf: values)
        let maximum = max(4, Int(asbd.mSampleRate * 0.25) * 4)
        if frames.count > maximum { frames.removeFirst(frames.count - maximum) }
        let now = ProcessInfo.processInfo.systemUptime
        guard now-lastUpdate > 0.2 else { return }
        lastUpdate = now
        let result = FOADirection.estimate(frames)
        let direction = result.bearing.map { String(format: "Encoder bearing %.0f°", $0) } ?? "Direction unknown"
        update(String(format: "Verified FOA · 4 channels · %.0f Hz · coherence %.2f", asbd.mSampleRate, result.coherence), direction)
    }
    private static func readFloats(_ sample: CMSampleBuffer) -> [Float]? {
        let frameCount = CMSampleBufferGetNumSamples(sample)
        guard frameCount > 0, frameCount <= 96000 else { return nil }
        var needed = 0
        CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(sample,
            bufferListSizeNeededOut: &needed, bufferListOut: nil, bufferListSize: 0,
            blockBufferAllocator: nil, blockBufferMemoryAllocator: nil, flags: 0, blockBufferOut: nil)
        guard needed > 0, needed < 4096 else { return nil }
        let raw = UnsafeMutableRawPointer.allocate(byteCount: needed, alignment: MemoryLayout<AudioBufferList>.alignment)
        defer { raw.deallocate() }
        let list = raw.bindMemory(to: AudioBufferList.self, capacity: 1)
        var retained: CMBlockBuffer?
        let result = CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(sample,
            bufferListSizeNeededOut: nil, bufferListOut: list, bufferListSize: needed,
            blockBufferAllocator: nil, blockBufferMemoryAllocator: nil, flags: 0, blockBufferOut: &retained)
        guard result == noErr else { return nil }
        return withExtendedLifetime(retained) {
            let buffers = UnsafeMutableAudioBufferListPointer(list)
            if buffers.count == 1, buffers[0].mNumberChannels == 4,
               buffers[0].mDataByteSize >= frameCount * 16, let data = buffers[0].mData {
                return Array(UnsafeBufferPointer(start: data.assumingMemoryBound(to: Float.self), count: frameCount * 4))
            }
            guard buffers.count == 4 else { return nil }
            var interleaved = [Float](repeating: 0, count: frameCount*4)
            for channel in 0..<4 {
                guard buffers[channel].mNumberChannels == 1,
                      buffers[channel].mDataByteSize >= frameCount*4,
                      let data = buffers[channel].mData else { return nil }
                let samples = data.assumingMemoryBound(to: Float.self)
                for frame in 0..<frameCount { interleaved[frame*4+channel] = samples[frame] }
            }
            return interleaved
        }
    }

}
private enum ProbeError: LocalizedError {
    case message(String)
    var errorDescription: String? { if case let .message(text) = self { return text }; return nil }
}
