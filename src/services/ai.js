import { GoogleGenAI } from '@google/genai';
import Groq from 'groq-sdk';
import { env } from '../config/env.js';

let geminiClient = null;
let groqClient = null;

/**
 * Initialize Google Gemini Client
 */
export function getGeminiClient() {
  if (!geminiClient) {
    if (!env.geminiApiKey) {
      throw new Error('GEMINI_API_KEY is not configured in .env.local');
    }
    geminiClient = new GoogleGenAI({ apiKey: env.geminiApiKey });
  }
  return geminiClient;
}

/**
 * Initialize Groq Client
 */
export function getGroqClient() {
  if (!groqClient) {
    if (!env.groqApiKey) {
      throw new Error('GROQ_API_KEY is not configured in .env.local');
    }
    groqClient = new Groq({ apiKey: env.groqApiKey });
  }
  return groqClient;
}

/**
 * Generate text using Gemini
 */
export async function generateGeminiText(prompt, modelName = 'gemini-2.5-flash') {
  const client = getGeminiClient();
  const response = await client.models.generateContent({
    model: modelName,
    contents: prompt
  });
  return response.text;
}

/**
 * Generate text using Groq
 */
export async function generateGroqText(prompt, modelName = 'llama-3.3-70b-versatile') {
  const client = getGroqClient();
  const completion = await client.chat.completions.create({
    messages: [{ role: 'user', content: prompt }],
    model: modelName
  });
  return completion.choices[0]?.message?.content || '';
}
