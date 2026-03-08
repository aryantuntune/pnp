import api from './api';

export interface PaymentConfig {
  gateway: string;
  configured: boolean;
}

export interface PaymentOrder {
  payment_url: string;
  client_txn_id: string;
  method: string;
}

export async function getPaymentConfig(): Promise<PaymentConfig> {
  const { data } = await api.get<PaymentConfig>('/api/portal/payment/config');
  return data;
}

export async function createPaymentOrder(bookingId: number): Promise<PaymentOrder> {
  const { data } = await api.post<PaymentOrder>('/api/portal/payment/create-order', {
    booking_id: bookingId,
    platform: 'mobile',
  });
  return data;
}
