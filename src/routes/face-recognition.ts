// src/routes/face-recognition.ts
import express from 'express';
import { getFaceRecognition } from '../utils/face-processor';

const router = express.Router();

router.post('/authenticate', async (req, res) => {
  const { image_buffer } = req.body;

  if (!image_buffer) {
    return res.status(400).json({ error: 'No image provided' });
  }

  try {
    const faceRecognition = getFaceRecognition();
    const queryEmbedding = faceRecognition.getEmbedding(Buffer.from(image_buffer, 'base64'));

    // Simulate stored persons
    const mockPersons = [
      { id: '1', name: 'Motty Admin', embedding: faceRecognition.getEmbedding(Buffer.from('admin-data')) },
      { id: '2', name: 'Ravi Worker', embedding: faceRecognition.getEmbedding(Buffer.from('worker-data')) }
    ];

    let bestMatch: any = null;
    let bestSimilarity = 0;

    for (const person of mockPersons) {
      const similarity = faceRecognition.compare(queryEmbedding, person.embedding);
      if (similarity > bestSimilarity) {  // ✅ Now valid: number > number
        bestSimilarity = similarity;
        bestMatch = person;
      }
    }

    if (bestMatch && bestSimilarity > 0.6) {
      res.json({
        authenticated: true,
        person_id: bestMatch.id,
        name: bestMatch.name,
        confidence: bestSimilarity
      });
    } else {
      res.json({
        authenticated: false,
        error: 'Face not recognized'
      });
    }
  } catch (err) {
    console.error('Face auth error:', err);
    res.status(500).json({ error: 'Authentication failed' });
  }
});

export default router;