import SwiftUI

struct ContentView: View {
    @StateObject private var probe = ProbeController()
    @Environment(\.scenePhase) private var phase
    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            Text("Aware spatial probe").font(.title2)
            Text(probe.reading).font(.largeTitle)
            Text(probe.status)
            Text("Experimental encoder-frame estimate. Angle, sign and phone orientation need calibration. This does not control alerts.").foregroundStyle(.secondary)
            Button(probe.running ? "Stop microphone" : "Test spatial mic for 8 seconds") {
                if probe.running { probe.stop() } else { probe.start() }
            }.buttonStyle(.borderedProminent)
            Text("No audio is saved or uploaded. Use a stationary phone and one sound source at a time. Test front, right, behind and left.").font(.footnote)
        }.padding(28)
        .onChange(of: phase) { _, next in if next != .active { probe.stop() } }
        .onDisappear { probe.stop() }
    }
}
