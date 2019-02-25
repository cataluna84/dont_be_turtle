//
//  PoseView.swift
//  Turtle-InfoBeans
//
//  Created by Mayank Bhaskar on 2/25/19.
//  Copyright © 2019 InfoBeans. All rights reserved.
//

import UIKit

class PoseView: UIView {
    
    var keypointLabelBGViews: [UIView] = []
    
    var bodyPoints: [ViewController.BodyPoint?] = [] {
        didSet {
            self.setNeedsDisplay()
            self.drawKeypoints(with: bodyPoints)
        }
    }
    
    func setUpOutputComponent() {
        
        keypointLabelBGViews = Constant.colors.map { color in
            let v = UIView(frame: CGRect(x: 0, y: 0, width: 4, height: 4))
            v.backgroundColor = color
            v.clipsToBounds = false
            let l = UILabel(frame: CGRect(x: 4 + 3, y: -3, width: 100, height: 8))
            l.text = Constant.pointLabels[Constant.colors.firstIndex(where: {$0 == color})!]
            l.textColor = color
            l.font = UIFont.preferredFont(forTextStyle: .caption2)
            v.addSubview(l)
            self.addSubview(v)
            return v
        }
        
        var x: CGFloat = 0.0
        let y: CGFloat = self.frame.size.height - 24
        let _ = Constant.colors.map { color in
            let index = Constant.colors.firstIndex(where: { color == $0 })
            if index == 2 || index == 8 { x += 28 }
            else { x += 14 }
            let v = UIView(frame: CGRect(x: x, y: y + 10, width: 4, height: 4))
            v.backgroundColor = color
            
            self.addSubview(v)
            return
        }
    }
    
    override func draw(_ rect: CGRect) {
        
        if let ctx = UIGraphicsGetCurrentContext() {
            
            ctx.clear(rect);
            
//            drawLine(ctx: ctx, from: CGPoint(x: 10, y: 20), to: CGPoint(x: 100, y: 20), color: UIColor.red.cgColor)
//            drawLine(ctx: ctx, from: CGPoint(x: 110, y: 120), to: CGPoint(x: 200, y: 120), color: UIColor.blue.cgColor)
            let size = self.bounds.size
            
            let color = Constant.jointLineColor.cgColor
            
            // MARK: Will have to change the bodypoint counts here or map the four detected points through other methods
            if Constant.pointLabels.count == bodyPoints.count {
                let _ = Constant.connectingPointIndexs.map { pIndex1, pIndex2 in
                    if let bp1 = self.bodyPoints[pIndex1], bp1.confidence > 0.0,
                        let bp2 = self.bodyPoints[pIndex2], bp2.confidence > 0.0 {
                        let p1 = bp1.point
                        let p2 = bp2.point
                        let point1 = CGPoint(x: (p1.x) * size.width, y: p1.y*size.height)
                        let point2 = CGPoint(x: (p2.x) * size.width, y: p2.y*size.height)
                        drawLine(ctx: ctx, from: point1, to: point2, color: color)
                    }
                }
            }
        }
    }
    
    func drawLine(ctx: CGContext, from p1: CGPoint, to p2: CGPoint, color: CGColor) {
        ctx.setStrokeColor(color)
        ctx.setLineWidth(3.0)
        
        ctx.move(to: p1)
        ctx.addLine(to: p2)
        
        ctx.strokePath();
    }
    
    func drawKeypoints(with n_kpoints: [ViewController.BodyPoint?]) {
        let imageFrame = keypointLabelBGViews.first?.superview?.frame ?? .zero
        
        let minAlpha: CGFloat = 1.0//0.4
        let maxAlpha: CGFloat = 1.0
        let maxC: Double = 0.6
        let minC: Double = 0.1
        
        for (index, kp) in n_kpoints.enumerated() {
            if let n_kp = kp {
                let x = n_kp.point.x * imageFrame.width
                let y = n_kp.point.y * imageFrame.height
                keypointLabelBGViews[index].center = CGPoint(x: x, y: y)
                let cRate = (n_kp.confidence - minC)/(maxC - minC)
                keypointLabelBGViews[index].alpha = (maxAlpha - minAlpha) * CGFloat(cRate) + minAlpha
            } else {
                keypointLabelBGViews[index].center = CGPoint(x: -4000, y: -4000)
                keypointLabelBGViews[index].alpha = minAlpha
            }
        }
    }
}

struct Constant {
    
    static let pointLabels = [
        "top\t\t\t", //0
        "neck\t\t", //1
        
        "R shoulder\t", //2
//        "R elbow\t\t", //3
//        "R wrist\t\t", //4
        "L shoulder\t", //5
//        "L elbow\t\t", //6
//        "L wrist\t\t", //7
//
//        "R hip\t\t", //8
//        "R knee\t\t", //9
//        "R ankle\t\t", //10
//        "L hip\t\t", //11
//        "L knee\t\t", //12
//        "L ankle\t\t", //13
    ]
    
    static let connectingPointIndexs: [(Int, Int)] = [
        (0, 1), // top-neck
        
        (1, 2), // neck-rshoulder
//        (2, 3), // rshoulder-relbow
//        (3, 4), // relbow-rwrist
//        (1, 8), // neck-rhip
//        (8, 9), // rhip-rknee
//        (9, 10), // rknee-rankle
        
        (1, 3), // neck-lshoulder       // MARK: replacing 5-lshoulder with 3-lshoulder
//        (5, 6), // lshoulder-lelbow
//        (6, 7), // lelbow-lwrist
//        (1, 11), // neck-lhip
//        (11, 12), // lhip-lknee
//        (12, 13), // lknee-lankle
    ]
    
    static let jointLineColor: UIColor = UIColor(displayP3Red: 87.0/255.0,
                                                 green: 255.0/255.0,
                                                 blue: 211.0/255.0,
                                                 alpha: 0.5)
    
    static let colors: [UIColor] = [
        .red,
        .green,
        .blue,
        .cyan,
//        .yellow,
//        .magenta,
//        .orange,
//        .purple,
//        .brown,
//        .black,
//        .darkGray,
//        .lightGray,
//        .white,
//        .gray,
    ]
}
