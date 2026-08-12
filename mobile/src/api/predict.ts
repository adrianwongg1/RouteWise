import { API_BASE_URL } from '../constants/config';
import { PredictRequest, PredictResponse } from '../types';
import { postJSON } from './client';

export async function predict(req: PredictRequest): Promise<PredictResponse> {
  return postJSON<PredictResponse>(`${API_BASE_URL}/predict`, req);
}
