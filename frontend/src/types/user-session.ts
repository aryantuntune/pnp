export interface ActiveSession {
  id: number;
  user_id: string;
  session_id: string;
  started_at: string | null;
  last_heartbeat: string | null;
  ip_address: string | null;
  city: string | null;
  user_agent: string | null;
  full_name: string;
  username: string;
  role: string;
  ticket_count: number | null;
}

export interface SessionHistory extends ActiveSession {
  ended_at: string | null;
  end_reason: string | null;
}

export interface SessionUser {
  id: string;
  full_name: string;
  username: string;
  role: string;
}
