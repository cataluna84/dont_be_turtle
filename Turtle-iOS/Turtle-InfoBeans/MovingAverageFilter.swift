//
//  MovingAverageFilter.swift
//  Turtle-InfoBeans
//
//  Created by Mayank Bhaskar on 2/25/19.
//  Copyright © 2019 InfoBeans. All rights reserved.
//

import Foundation
import UIKit

public class MovingAverageFilter {
    typealias BodyPoint = ViewController.BodyPoint
    
    let maximumCount: Int = 8
    var keypointsArray: [[BodyPoint?]] = []
    
    func addKeypoints(keypoints: [BodyPoint?]) {
        keypointsArray.append(keypoints)
        if keypointsArray.count > maximumCount {
            keypointsArray.remove(at: 0)
        }
    }
    
    var keypoints: [BodyPoint?] {
        if let firstKeypoints = keypointsArray.first {
            var result: [BodyPoint?] = Array<BodyPoint?>(repeating: nil, count: firstKeypoints.count)
            
            for i in 0..<firstKeypoints.count {
                var count: Double = 0
                
                for j in 0..<keypointsArray.count {
                    
                    if let kp: BodyPoint = keypointsArray[j][i] {
                        count += 1
                        if let oldkp: BodyPoint = result[i] {
                            let p = oldkp.point
                            let c = oldkp.confidence
                            result[i]?.point = CGPoint(x: p.x + kp.point.x, y: p.y + kp.point.y)
                            result[i]?.confidence = c + kp.confidence
                        } else {
                            result[i] = kp
                        }
                    }
                }
                
                if let kp = result[i] {
                    result[i]?.point = CGPoint(x: kp.point.x / CGFloat(count), y: kp.point.y / CGFloat(count))
                    result[i]?.confidence = kp.confidence / count
                }
            }
            return result
        } else {
            return []
        }
    }
}

class MovingAverageFilterAngle {
    
    let maximumCount: Int = 8
    var angles: [Double] = []
    
    func addAngle(newAngle: Double) {
        angles.append(newAngle)
        if angles.count > maximumCount {
            angles.remove(at: 0)
        }
    }
    
    var angle: Double {
        guard angles.count > 0 else { return 0 }
        return (angles.reduce(0) { $0 + $1 }) / Double(angles.count)
    }
}


extension Double {
    static func angle(p1: CGPoint, p2: CGPoint, p3: CGPoint) -> Double {
        let angle1: Double = Double(atan2(p1.y - p3.y, p1.x - p3.x));
        let angle2: Double = Double(atan2(p2.y - p3.y, p2.x - p3.x));
        
        return angle1 - angle2;
    }
    
    static func radianAngle(p1: CGPoint, p2: CGPoint, p3: CGPoint) -> Double {
        return (angle(p1: p1, p2: p2, p3: p3) / pi) * 180
    }
}
