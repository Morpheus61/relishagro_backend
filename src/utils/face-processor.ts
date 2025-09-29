// src/utils/face-processor.ts
import { FaceRecognitionModel } from '../models/face-recognition';

export function getFaceRecognition() {
  return FaceRecognitionModel.getInstance();
}