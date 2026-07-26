export type RightsBasis = 'written_permission' | 'platform_program' | 'counsel_approved' | 'internal_demo_only' | 'blocked';
export type CommercialStatus = 'approved' | 'conditional' | 'blocked' | 'expired';
export type SessionState = 'requested' | 'eligibility_checked' | 'offered' | 'accepted' | 'reserved' | 'launching' | 'signaling' | 'connecting' | 'live' | 'ending' | 'cleaned' | 'completed' | 'failed' | 'cancelled';
export type NodeState = 'pending_approval' | 'enrolled' | 'online_idle' | 'reserved' | 'launching' | 'streaming' | 'draining' | 'quarantined' | 'revoked' | 'error_cooldown';

export interface GameTitle {
  id: string;
  title: string;
  genre: string;
  cover_url: string;
  description: string;
  featured?: boolean;
  active_hosts_count: number;
  approval: {
    title_id: string;
    publisher: string;
    rights_basis: RightsBasis;
    commercial_status: CommercialStatus;
    support_tier: 'experimental' | 'supported' | 'suspended';
  };
  requirements: {
    gpu: string;
    min_vram_gb: number;
    encoder_required: string;
    recommended_downlink_mbps: number;
  };
}

export interface SessionStats {
  fps: number;
  resolution: string;
  bitrate_kbps: number;
  rtt_ms: number;
  packet_loss_pct: number;
  codec: string;
  connection_mode: 'direct_p2p' | 'turn_relay';
  frames_decoded: number;
  frames_dropped: number;
}

export interface PreflightResult {
  rtt_ms: number;
  jitter_ms: number;
  packet_loss_pct: number;
  estimated_bandwidth_mbps: number;
  connection_type: 'direct_p2p' | 'turn_relay';
  passed: boolean;
  reasons: string[];
}

export interface ProviderNode {
  node_id: string;
  name: string;
  state: NodeState;
  region: string;
  ping_ms: number;
  host_class: 'dedicated_test_machine' | 'managed_fleet' | 'trusted_partner';
  last_heartbeat_at: string;
  telemetry: {
    gpu_name: string;
    driver_version: string;
    gpu_utilization_pct: number;
    vram_used_gb: number;
    vram_total_gb: number;
    temp_celsius: number;
    power_draw_watts: number;
    fan_speed_pct: number;
  };
}

export interface HealthCheckResponse {
  status: 'ok' | 'degraded' | 'unreachable';
  db: 'ok' | 'unhealthy' | 'mock';
  version: string;
}

export type TabType = 'catalog' | 'session' | 'telemetry' | 'debugger';
