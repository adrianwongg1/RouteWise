import { API_BASE_URL } from '../constants/config';
import { SubscribeRequest, SubscribeResponse } from '../types';
import { postJSON } from './client';

export function subscribe(req: SubscribeRequest): Promise<SubscribeResponse> {
  return postJSON<SubscribeResponse>(`${API_BASE_URL}/subscribe`, req);
}
