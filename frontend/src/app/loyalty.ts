import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
export interface LoyaltyAccount {
  available: string; reserved: string; debt: string;
  balance_minor?: number; reserved_minor?: number; debt_minor?: number;
  total_earned_minor?: number; total_redeemed_minor?: number;
  level?: { code: string; cashback_percent: string; completed_orders: number; target_orders: number | null; next_level: string | null; orders_remaining: number; progress_percent: number; month: string };
  second_order?: { status: string; reward_minor: number; deadline: string | null; seconds_remaining: number; first_order_id: number | null; second_order_id: number | null; awarded_minor: number };
  policy: { base_percent: string; promotional_percent: string; spend_percent: string; silver_orders?: string; silver_percent?: string; gold_orders?: string; gold_percent?: string; second_order_days?: string; milestone_every?: string; milestone_minimum?: string; milestone_bonus?: string };
  entries: { id: number; order_id: number | null; order_number?: string | null; kind: string; category?: string; amount_minor?: number; available_delta: string; reserved_delta: string; debt_delta: string; created_at: string }[];
  completed_rewards?: { order_id: number; order_number: string; earned_minor: number }[];
  has_more?: boolean; next_before?: number | null;
}
@Injectable({ providedIn: 'root' })
export class Loyalty {
  constructor(private http: HttpClient) {}
  account(before?: number) { return this.http.get<LoyaltyAccount>('http://localhost:8000/api/loyalty/', before ? { params: { before } } : {}); }
}
