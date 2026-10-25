import AVFoundation
import AudioToolbox
import Combine
import Foundation
import Network

/// Spatial-direction probe: listens with the phone's FOA microphones until Stop (3 minute cap),
/// shows the dominant-sound direction, and can stream readings to the Mac receiver via the relay.
@MainActor final class ProbeController: ObservableObject {
    @Published var status = "Ready. No microphone capture has started."
    @Published var reading = "Direction unknown"
    @Published var detail = ""
    @Published var running = false
    @Published var sendStatus = "Not sending."
    @Published var frontOffset: Double? = UserDefaults.standard.object(forKey: "frontOffset") as? Double
    @Published var macAddress = UserDefaults.standard.string(forKey: "macAddress") ?? "http://10.60.22.103:5177" {
        didSet { UserDefaults.standard.set(macAddress, forKey: "macAddress") }
    }
    @Published var pairingCode = UserDefaults.standard.string(forKey: "pairingCode") ?? "" {
        didSet { UserDefaults.standard.set(pairingCode, forKey: "pairingCode") }
    }
    @Published var sending = false
    @Published var usbStatus = "USB: waiting for the Mac bridge."
    private let usb = UsbStream()

    private var engine: SpatialProbeEngine?
    private var generation = 0
    private var lastConfident: (raw: Double, coherence: Double, at: Date)?
    private var lastSent = Date.distantPast
    private var sentOK = 0

    init() {
        usb.onChange = { [weak self] clients in
            Task { @MainActor in
                guard let self else { return }
                self.usbStatus = clients == 0 ? "USB: waiting for the Mac bridge."
                    : self.running ? "USB: streaming to the Mac." : "USB: Mac connected. Tap Start listening to stream."
            }
        }
    }

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
            let next = SpatialProbeEngine { [weak self] status, result in
                Task { @MainActor in
                    guard let self, self.generation == version else { return }
                    self.handle(status: status, result: result)
                }
            }
            engine = next
            next.start()
            // Bounded test session, not a background recorder. No samples are saved.
            try? await Task.sleep(for: .seconds(180))
            if generation == version { stop() }
        }
    }

    func stop() {
        guard running || engine != nil else { return }
        let lastStatus = status
        generation += 1
        engine?.stop(); engine = nil; running = false
        status = "Stopped. No audio saved. Last input: \(lastStatus)"
        reading = "Direction unknown · microphone off"
        detail = ""
    }

    /// Point the phone's "front" at the last confident sound (clap in front of it, then tap).
    func setFront() {
        guard let last = lastConfident, Date().timeIntervalSince(last.at) < 5 else {
            detail = "Make a clear sound in front first, then tap Set front within 5 seconds."
            return
        }
        frontOffset = last.raw
        UserDefaults.standard.set(last.raw, forKey: "frontOffset")
        detail = "Front set. Directions are now relative to that sound."
    }

    func clearFront() {
        frontOffset = nil
        UserDefaults.standard.removeObject(forKey: "frontOffset")
    }

    func testConnection() {
        guard let url = URL(string: macAddress.trimmingCharacters(in: .whitespaces) + "/ping") else {
            sendStatus = "That address is not a URL."; return
        }
        var request = URLRequest(url: url, timeoutInterval: 3)
        request.setValue(pairingCode.uppercased(), forHTTPHeaderField: "X-Aware-Code")
        sendStatus = "Checking…"
        URLSession.shared.dataTask(with: request) { [weak self] _, response, error in
            let code = (response as? HTTPURLResponse)?.statusCode
            Task { @MainActor in
                self?.sendStatus = code == 200 ? "Mac reachable. Pairing code accepted."
                    : code == 403 ? "Mac reachable, but the pairing code is wrong."
                    : "Mac not reachable: \(error?.localizedDescription ?? "HTTP \(code ?? 0)")"
            }
        }.resume()
    }

    private func calibrated(_ raw: Double) -> Double? {
        guard let offset = frontOffset else { return nil }
        var value = raw - offset
        while value > 180 { value -= 360 }
        while value <= -180 { value += 360 }
        return value
    }

    private func side(_ degrees: Double) -> String {
        switch degrees {
        case -45...45: return "Front"
        case 45...135: return "Right"
        case -135 ... -45: return "Left"
        default: return "Behind"
        }
    }

    private func label(raw: Double) -> String {
        if let value = calibrated(raw) { return String(format: "%@ · %.0f°", side(value), value) }
        return String(format: "Encoder %.0f° · set front", raw)
    }

    private func handle(status: String, result: FOADirection?) {
        self.status = status
        guard let result else { return }
        let now = Date()
        if let raw = result.bearing {
            lastConfident = (raw, result.coherence, now)
            reading = label(raw: raw)
        } else if let last = lastConfident, now.timeIntervalSince(last.at) < 3 {
            reading = label(raw: last.raw) + String(format: " · %.0fs ago", now.timeIntervalSince(last.at))
        } else {
            reading = "Direction unknown"
        }
        detail = String(format: "coherence %.2f (needs 0.60) · level %.4f", result.coherence, result.rms)
        send(result, at: now)
    }

    private func body(_ result: FOADirection) -> [String: Any] {
        let bearing = result.bearing.flatMap(calibrated)
        return [
            "bearing_degrees": bearing as Any? ?? NSNull(),
            "coherence": min(1, max(0, result.coherence)),
            "rms": min(10, max(0, result.rms)),
            "calibrated": frontOffset != nil,
            "device": "johns-phone",
        ]
    }

    private func send(_ result: FOADirection, at now: Date) {
        // USB: every reading goes to any connected Mac bridge (scripts/phone_usb_bridge.py).
        if let line = try? JSONSerialization.data(withJSONObject: body(result)) {
            let clients = usb.send(line + Data([10]))
            usbStatus = clients > 0 ? "USB: streaming to the Mac." : "USB: waiting for the Mac bridge."
        }
        guard sending else { return }
        // Confident readings go out at up to 5 per second; otherwise one heartbeat per second.
        let interval = result.bearing == nil ? 1.0 : 0.2
        guard now.timeIntervalSince(lastSent) >= interval,
              let url = URL(string: macAddress.trimmingCharacters(in: .whitespaces) + "/spatial") else { return }
        lastSent = now
        var request = URLRequest(url: url, timeoutInterval: 1.5)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(pairingCode.uppercased(), forHTTPHeaderField: "X-Aware-Code")
        request.httpBody = try? JSONSerialization.data(withJSONObject: body(result))
        URLSession.shared.dataTask(with: request) { [weak self] _, response, error in
            let code = (response as? HTTPURLResponse)?.statusCode
            Task { @MainActor in
                guard let self else { return }
                if code == 200 {
                    self.sentOK += 1
                    self.sendStatus = self.frontOffset == nil
                        ? "Connected · \(self.sentOK) sent · set front so the Mac can use directions"
                        : "Sending to Mac · \(self.sentOK) readings"
                } else {
                    self.sendStatus = code == 403 ? "Pairing code rejected."
                        : "Send failed: \(error?.localizedDescription ?? "HTTP \(code ?? 0)")"
                }
            }
        }.resume()
    }
}

/// Newline-delimited JSON readings on TCP 5178. The Mac reaches it through the USB cable (usbmux),
/// so no Wi-Fi is involved. Only direction numbers are sent, never audio.
final class UsbStream: @unchecked Sendable {
    private let queue = DispatchQueue(label: "aware.usb.stream")
    private var listener: NWListener?
    private var clients: [NWConnection] = []
    private var count = 0
    var onChange: (@Sendable (Int) -> Void)?

    init() {
        guard let port = NWEndpoint.Port(rawValue: 5178), let listener = try? NWListener(using: .tcp, on: port) else { return }
        listener.newConnectionHandler = { [weak self] connection in
            guard let self else { return }
            connection.stateUpdateHandler = { [weak self, weak connection] state in
                guard let self, let connection else { return }
                if case .failed = state { self.drop(connection) }
                if case .cancelled = state { self.drop(connection) }
            }
            connection.start(queue: self.queue)
            self.clients.append(connection)
            self.count = self.clients.count
            self.onChange?(self.count)
        }
        listener.start(queue: queue)
        self.listener = listener
    }

    private func drop(_ connection: NWConnection) {
        clients.removeAll { $0 === connection }
        count = clients.count
        onChange?(count)
    }

    /// Returns how many bridges were connected when the line was queued.
    func send(_ data: Data) -> Int {
        queue.async {
            for connection in self.clients {
                connection.send(content: data, completion: .contentProcessed { [weak self, weak connection] error in
                    guard error != nil, let self, let connection else { return }
                    connection.cancel()
                    self.drop(connection)
                })
            }
        }
        return count
    }
}

private final class SpatialProbeEngine: NSObject, AVCaptureAudioDataOutputSampleBufferDelegate, @unchecked Sendable {
    private let session = AVCaptureSession()
    private let queue = DispatchQueue(label: "aware.spatial.probe")
    private let update: @Sendable (String, FOADirection?) -> Void
    private var lastUpdate = 0.0
    private var frames: [Float] = []
    init(update: @escaping @Sendable (String, FOADirection?) -> Void) { self.update = update }
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
            update("Listening · FOA requested", nil)
        } catch { update("Capture unavailable: \(error.localizedDescription)", nil) }
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
            update("Unexpected sample format; refusing to guess channel order", nil); return
        }
        guard let values = Self.readFloats(sampleBuffer) else {
            update("Could not decode native audio buffers", nil); return
        }
        frames.append(contentsOf: values)
        let maximum = max(4, Int(asbd.mSampleRate * 0.25) * 4)
        if frames.count > maximum { frames.removeFirst(frames.count - maximum) }
        let now = ProcessInfo.processInfo.systemUptime
        guard now-lastUpdate > 0.2 else { return }
        lastUpdate = now
        let block = Int(asbd.mSampleRate * 0.04)  // 40 ms: long enough to hold a knock, short enough to exclude the room
        update(String(format: "Verified FOA · 4 channels · %.0f Hz", asbd.mSampleRate),
               FOADirection.loudestBlock(frames, blockFrames: block))
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
