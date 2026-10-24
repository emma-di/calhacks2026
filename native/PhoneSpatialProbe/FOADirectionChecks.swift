import Foundation

@main struct DirectionChecks {
    static func main() {
        var cases = 0
        for degrees in stride(from: -180, to: 180, by: 5) {
            let theta = Double(degrees) * .pi / 180
            var pcm: [Float] = []
            for frame in 0..<2048 {
                let s = Float(sin(Double(frame)*0.13))
                pcm += [s, -s*Float(sin(theta)), 0, s*Float(cos(theta))]
            }
            let result = FOADirection.estimate(pcm)
            guard let bearing = result.bearing else { fatalError("Missing ideal bearing") }
            let difference = abs(atan2(sin((bearing-Double(degrees)) * .pi/180), cos((bearing-Double(degrees)) * .pi/180))*180 / .pi)
            precondition(difference < 0.001, "Wrong angle/sign/order")
            cases += 1
        }
        for pcm: [Float] in [[], [0,0,0,0], [1,2,3], [.nan,0,0,0], [.infinity,0,0,0], [1,0,1,0], [1,0,0,0]] {
            precondition(FOADirection.estimate(pcm).bearing == nil)
            cases += 1
        }
        // Two equal opposing plane waves can cancel direction even with audible pressure.
        precondition(FOADirection.estimate([1,0,0,0,-1,0,0,0]).bearing == nil)
        // A 40 ms knock from the right inside a quarter second of diffuse room noise (48 kHz).
        var seed: UInt32 = 7
        func noise() -> Float { seed = seed &* 1664525 &+ 1013904223; return Float(Int32(bitPattern: seed)) / Float(Int32.max) * 0.3 }
        var room: [Float] = []
        for frame in 0..<12000 {
            if (6000..<7920).contains(frame) {
                let s = Float(sin(Double(frame) * 0.9)) * (frame % 2 == 0 ? 1 : 0.6)
                room += [s + noise(), -s + noise(), noise(), noise()]   // ACN: Y = -s points right
            } else {
                room += [noise(), noise(), noise(), noise()]
            }
        }
        let whole = FOADirection.estimate(room)
        let knock = FOADirection.loudestBlock(room, blockFrames: 1920)
        guard let bearing = knock.bearing else { fatalError("Loudest block missed the knock (coherence \(knock.coherence))") }
        precondition(abs(bearing - 90) < 15, "Knock bearing \(bearing) should be near +90 (right)")
        precondition(knock.coherence > whole.coherence, "The knock block should be more coherent than the whole window")
        cases += 1
        print("FOA checks passed: \(cases+1) synthetic cases. Real-device calibration still required.")
    }
}
