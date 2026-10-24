import SwiftUI

struct ContentView: View {
    @StateObject private var probe = ProbeController()
    @Environment(\.scenePhase) private var phase
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("Aware spatial probe").font(.title2)
                Text(probe.reading).font(.largeTitle).minimumScaleFactor(0.5).lineLimit(2)
                Text(probe.detail).font(.callout).foregroundStyle(.secondary)
                Text(probe.status)
                Button(probe.running ? "Stop microphone" : "Start listening") {
                    if probe.running { probe.stop() } else { probe.start() }
                }.buttonStyle(.borderedProminent)
                HStack {
                    Button("Set front") { probe.setFront() }.buttonStyle(.bordered).disabled(!probe.running)
                    if probe.frontOffset != nil { Button("Clear front") { probe.clearFront() }.buttonStyle(.bordered) }
                }
                Text("Lay the phone flat and still. Clap once in front of it, then tap Set front. Directions are then front, right, behind or left of that.")
                    .font(.footnote)

                Divider()
                Text("Send to Mac").font(.headline)
                TextField("Relay address", text: $probe.macAddress)
                    .textFieldStyle(.roundedBorder).keyboardType(.URL)
                    .textInputAutocapitalization(.never).autocorrectionDisabled()
                TextField("Pairing code", text: $probe.pairingCode)
                    .textFieldStyle(.roundedBorder).textInputAutocapitalization(.characters).autocorrectionDisabled()
                HStack {
                    Button("Test connection") { probe.testConnection() }.buttonStyle(.bordered)
                    Toggle("Send directions", isOn: $probe.sending)
                }
                Text(probe.sendStatus).font(.callout).foregroundStyle(.secondary)
                Text("Experimental: angles come from the phone's spatial microphones and need calibration. Sends only direction numbers, never audio. Listening stops after 3 minutes, on Stop, or when the app leaves the screen.")
                    .font(.footnote).foregroundStyle(.secondary)
            }.padding(24)
        }
        .onChange(of: phase) { _, next in if next != .active { probe.stop() } }
        .onDisappear { probe.stop() }
    }
}
