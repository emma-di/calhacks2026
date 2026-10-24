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
        print("FOA checks passed: \(cases+1) synthetic cases. Real-device calibration still required.")
    }
}
