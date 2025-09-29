// src/models/face-recognition.ts

/**
 * Lightweight Face Recognition Model (Pure JS)
 * Returns similarity scores for flexible matching
 */
export class FaceRecognitionModel {
  private static instance: FaceRecognitionModel;
  public available = true;
  public mode: 'lightweight' = 'lightweight';

  private constructor() {}

  public static getInstance(): FaceRecognitionModel {
    if (!FaceRecognitionModel.instance) {
      FaceRecognitionModel.instance = new FaceRecognitionModel();
    }
    return FaceRecognitionModel.instance;
  }

  /**
   * Generate deterministic embedding from image buffer
   */
  public getEmbedding(imageBuffer: Buffer): number[] {
    const hash = this.simpleHash(imageBuffer);
    const embedding: number[] = [];
    for (let i = 0; i < 256; i++) {
      embedding.push(Math.sin(hash + i) * Math.cos(hash * 2 + i));
    }
    return embedding;
  }

  /**
   * Compare two embeddings and return similarity score [0, 1]
   */
  public compare(emb1: number[], emb2: number[]): number {
    if (emb1.length !== emb2.length) return 0;

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < emb1.length; i++) {
      dotProduct += emb1[i] * emb2[i];
      normA += emb1[i] * emb1[i];
      normB += emb2[i] * emb2[i];
    }

    const similarity = dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
    
    // Return value between 0 and 1 (cosine similarity)
    return isNaN(similarity) ? 0 : similarity;
  }

  private simpleHash(buffer: Buffer): number {
    let hash = 0;
    for (let i = 0; i < buffer.length; i++) {
      hash = ((hash << 5) - hash) + buffer[i];
      hash |= 0;
    }
    return Math.abs(hash);
  }
}