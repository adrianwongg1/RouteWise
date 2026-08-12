export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface PredictByFlightRequest {
  flight_iata: string;
  flight_date: string;
}

export interface PredictByRouteRequest {
  origin: string;
  destination: string;
  flight_date: string;
  departure_time: string;
}

export type PredictRequest = PredictByFlightRequest | PredictByRouteRequest;

export interface PredictResponse {
  flight_iata: string;
  flight_date: string;
  airline: string;
  origin: string;
  destination: string;
  scheduled_departure: string | null;
  current_status: string | null;
  current_delay_minutes: number | null;
  predicted_probability: number;
  risk_level: RiskLevel;
  explanation: string;
}

export interface SubscribeRequest {
  push_token: string;
  flight_iata: string;
  flight_date: string;
  origin: string;
  destination: string;
  airline: string;
  scheduled_departure: string;
  predicted_risk: number;
}

export interface SubscribeResponse {
  subscribed: boolean;
}
