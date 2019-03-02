//
//  ViewController.swift
//  Turtle-InfoBeans
//
//  Created by Mayank Bhaskar on 2/25/19.
//  Copyright © 2019 InfoBeans. All rights reserved.
//

import UIKit
import Vision
import CoreMedia

class ViewController: UIViewController {
    
    public typealias BodyPoint = (point: CGPoint, confidence: Double)
    public typealias DetectObjectsCompletion = ([BodyPoint?]?, Error?) -> Void
    
    // MARK: - UI Properties
    
    @IBOutlet weak var videoPreview: UIView!
    @IBOutlet weak var poseView: PoseView!
    @IBOutlet weak var labelsTableView: UITableView!
    
    @IBOutlet weak var inferenceLabel: UILabel!
    @IBOutlet weak var etimeLabel: UILabel!
    @IBOutlet weak var fpsLabel: UILabel!
    
    @IBOutlet weak var turtleBGView: UIView!
    @IBOutlet weak var angleLabel: UILabel!
    
    private var tableData: [BodyPoint?] = []
    
    private var mvFilter: MovingAverageFilter = MovingAverageFilter()
    private var mvFilterAngle: MovingAverageFilterAngle = MovingAverageFilterAngle()
    
    // MARK - Performance measurement properties
    private let 👨‍🔧 = 📏()
    
    
    // MARK - Core ML model
    // model_itr184400_b32_d25 - Is able to accurately detect the left shoulder, whereas the labels on neck, top and right shoulder need more iterations
    typealias EstimationModel = model_itr184400_b32_d25
    var coremlModel: EstimationModel? = nil
    
    
    
    // MARK: - Vision
    var request: VNCoreMLRequest!
    var visionModel: VNCoreMLModel! {
        didSet {
            request = VNCoreMLRequest(model: visionModel, completionHandler: visionRequestDidComplete)
            request.imageCropAndScaleOption = .centerCrop
        }
    }
    
    
    // MARK: - AV Properties
    
    var videoCapture: VideoCapture!
    let semaphore = DispatchSemaphore(value: 2)
    
    
    // MARK: - Life cycle methods
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        //        self.title = "lsp chk 370000"
        
        // The MobileNet class puts `MobileNet.mlmodel` in the project and builds the automatically generated wrapper class
        // model created in MobileNet: create VNCoreMLModel object (to be used in Vision) with MLModel object
        // Vision automatically adjusts to the input size of the model (image size)
        visionModel = try? VNCoreMLModel(for: EstimationModel().model)
        
        // Camera settings
        setUpCamera()
        
        // Label table setting
        labelsTableView.dataSource = self
        
        // Set label points
        poseView.setUpOutputComponent()
        
        // Delegate settings for performance measurement
        👨‍🔧.delegate = self
    }
    
    override func didReceiveMemoryWarning() {
        super.didReceiveMemoryWarning()
    }
    
    
    // MARK: - Initial setting
    
    func setUpCamera() {
        videoCapture = VideoCapture()
        videoCapture.delegate = self
        videoCapture.fps = 30
        videoCapture.setUp(sessionPreset: .vga640x480) { success in
            
            if success {
                // Put video preview view in UI
                if let previewLayer = self.videoCapture.previewLayer {
                    self.videoPreview.layer.addSublayer(previewLayer)
                    self.resizePreviewLayer()
                }
                
                // After initial setup, you can start live video
                self.videoCapture.start()
            }
        }
    }
    
    func resizePreviewLayer() {
        videoCapture.previewLayer?.frame = videoPreview.bounds
    }
}

// MARK: - For VideoCaptureDelegate and predicting BodyPoints
extension ViewController: VideoCaptureDelegate {
    
    func videoCapture(_ capture: VideoCapture, didCaptureVideoFrame pixelBuffer: CVPixelBuffer?, timestamp: CMTime) {
        // The captured image from the camera is stored in the pixelBuffer.
        // Vision framework allows you to use pixelBuffer directly instead of image
        if let pixelBuffer = pixelBuffer {
            // start of measure
            self.👨‍🔧.🎬👏()
            
            // predict!
            self.predictUsingVision(pixelBuffer: pixelBuffer)
        }
    }
    
    func predictUsingVision(pixelBuffer: CVPixelBuffer) {
        // Vision will automatically resize the input image.
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer)
        try? handler.perform([request])
    }
    
    func visionRequestDidComplete(request: VNRequest, error: Error?) {
        self.👨‍🔧.🏷(with: "endInference")
        if let observations = request.results as? [VNCoreMLFeatureValueObservation],
            let heatmap = observations.first?.featureValue.multiArrayValue {
            
            // convert heatmap to [keypoint]
            let n_kpoints = convert(heatmap: heatmap)
            
            self.mvFilter.addKeypoints(keypoints: n_kpoints)
            
            
            // MARK: Changed from keypoints to n_kpoints
            let filetered_kpoints = self.mvFilter.keypoints
            //            let filetered_kpoints = n_kpoints
            
            DispatchQueue.main.sync {
                // draw line
                self.poseView.bodyPoints = filetered_kpoints
                
                // show key points description in tableview
                self.showKeypointsDescription(with: n_kpoints)
                
                self.turtleBGView.alpha = 0.6
                if let p1: CGPoint = filetered_kpoints[0]?.point,
                    let p2: CGPoint = filetered_kpoints[2]?.point,
                    let p3: CGPoint = filetered_kpoints[1]?.point {
                    
                    let result: Double = Double.radianAngle(p1: p1, p2: p2, p3: p3)
                    mvFilterAngle.addAngle(newAngle: result)
                    let angle = mvFilterAngle.angle
                    self.angleLabel.text = "\(String(format: "%.1f", angle))"
                    if abs(angle) > 284 {
                        self.turtleBGView.backgroundColor = .red
                    } else {
                        self.turtleBGView.backgroundColor = .green
                    }
                }
                
                // end of measure
                self.👨‍🔧.🎬🤚()
            }
        }
    }
    
    
    // MARK: convert heatmap to [keypoint]
    func convert(heatmap: MLMultiArray) -> [BodyPoint?] {
        guard heatmap.shape.count >= 3 else {
            print("heatmap's shape is invalid. \(heatmap.shape)")
            return []
        }
        let keypoint_number = heatmap.shape[0].intValue
        let heatmap_w = heatmap.shape[1].intValue
        let heatmap_h = heatmap.shape[2].intValue
        
        var n_kpoints = (0..<keypoint_number).map { _ -> BodyPoint? in
            return nil
        }
        
        for k in 0..<keypoint_number {
            for i in 0..<heatmap_w {
                for j in 0..<heatmap_h {
                    let index = k*(heatmap_w*heatmap_h) + i*(heatmap_h) + j
                    let confidence = heatmap[index].doubleValue
                    guard confidence > 0 else { continue }
                    if n_kpoints[k] == nil ||
                        (n_kpoints[k] != nil && n_kpoints[k]!.confidence < confidence) {
                        n_kpoints[k] = (CGPoint(x: CGFloat(j), y: CGFloat(i)), confidence)
                    }
                }
            }
        }
        
        // transpose to (1.0, 1.0)
        n_kpoints = n_kpoints.map { kpoint -> BodyPoint? in
            if let kp = kpoint {
                return (CGPoint(x: 1 - kp.point.x/CGFloat(heatmap_w),
                                y: kp.point.y/CGFloat(heatmap_h)),
                        kp.confidence)
            } else {
                return nil
            }
        }
        
        return n_kpoints
    }
    
    func showKeypointsDescription(with n_kpoints: [BodyPoint?]) {
        self.tableData = n_kpoints
        self.labelsTableView.reloadData()
    }
}


// MARK: - UITableViewDataSource
extension ViewController: UITableViewDataSource {
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return tableData.count// > 0 ? 1 : 0
    }
    
    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell: UITableViewCell = tableView.dequeueReusableCell(withIdentifier: "LabelCell", for: indexPath)
        cell.textLabel?.text = Constant.pointLabels[indexPath.row]
        if let body_point = tableData[indexPath.row] {
            let pointText: String = "\(String(format: "%.3f", body_point.point.x)), \(String(format: "%.3f", body_point.point.y))"
            cell.detailTextLabel?.text = "(\(pointText)), [\(String(format: "%.3f", body_point.confidence))]"
        } else {
            cell.detailTextLabel?.text = "N/A"
        }
        return cell
    }
}


extension ViewController: 📏Delegate {
    func updateMeasure(inferenceTime: Double, executionTime: Double, fps: Int) {
        //print(executionTime, fps)
        self.inferenceLabel.text = "inference: \(Int(inferenceTime*1000.0)) mm"
        self.etimeLabel.text = "execution: \(Int(executionTime*1000.0)) mm"
        self.fpsLabel.text = "fps: \(fps)"
    }
}
