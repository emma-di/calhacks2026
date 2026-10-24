import Foundation

/// Experimental acoustic-vector estimate for ACN/SN3D W,Y,Z,X samples.
/// This is encoder-frame bearing, NOT a calibrated wearer bearing or probability.
struct FOADirection {
    let bearing: Double?
    let coherence: Double
    let rms: Double

    static func estimate(_ samples: [Float]) -> FOADirection {
        guard !samples.isEmpty, samples.count % 4 == 0,
              samples.allSatisfy({ $0.isFinite }) else {
            return FOADirection(bearing: nil, coherence: 0, rms: 0)
        }
        var ww = 0.0, dd = 0.0, wx = 0.0, wy = 0.0, wz = 0.0
        for i in stride(from: 0, to: samples.count, by: 4) {
            let w = Double(samples[i]), y = Double(samples[i+1])
            let z = Double(samples[i+2]), x = Double(samples[i+3])
            ww += w*w; dd += x*x+y*y+z*z
            wx += w*x; wy += w*y; wz += w*z
        }
        let rms = sqrt(ww / Double(samples.count/4))
        let total = sqrt(wx*wx+wy*wy+wz*wz)
        let horizontal = hypot(wx, wy)
        let coherence = min(1, total / max(1e-30, sqrt(ww*dd)))
        guard rms >= 1e-5, coherence >= 0.6, horizontal > total * 0.2 else {
            return FOADirection(bearing: nil, coherence: coherence, rms: rms)
        }
        // ACN Y points left; Aware uses clockwise/right-positive bearings.
        return FOADirection(bearing: atan2(-wy, wx)*180 / .pi, coherence: coherence, rms: rms)
    }
}
