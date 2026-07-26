import type {
  GameTitle,
  ProviderNode,
  HealthCheckResponse,
  PreflightResult,
  SessionState,
} from '../types';

// ---------------------------------------------------------------------------
// Mock catalog — 3 titles
// ---------------------------------------------------------------------------

export const MOCK_CATALOG: GameTitle[] = [
  {
    id: 'gt-001',
    title: 'Stellar Odyssey',
    genre: 'Sci-Fi RPG',
    cover_url: 'https://images.unsplash.com/photo-1534996858221-380b92700493?w=400&h=600&fit=crop',
    description:
      'Explore a vast procedurally-generated galaxy in this open-world sci-fi RPG. Command your starship, forge alliances with alien civilizations, and unravel an ancient mystery threatening the fabric of space-time.',
    featured: true,
    active_hosts_count: 12,
    approval: {
      title_id: 'gt-001',
      publisher: 'Nebula Interactive',
      rights_basis: 'written_permission',
      commercial_status: 'approved',
      support_tier: 'supported',
    },
    requirements: {
      gpu: 'NVIDIA RTX 3080 or higher',
      min_vram_gb: 10,
      encoder_required: 'NVENC H.265',
      recommended_downlink_mbps: 35,
    },
  },
  {
    id: 'gt-002',
    title: 'Apex Circuit',
    genre: 'Racing Sim',
    cover_url: 'https://images.unsplash.com/photo-1511919884226-fd3cad34687c?w=400&h=600&fit=crop',
    description:
      'Experience hyper-realistic motorsport with laser-scanned circuits, dynamic weather, and a full FIA-licensed championship season. Every tire compound, brake temperature, and aero setup matters.',
    featured: false,
    active_hosts_count: 7,
    approval: {
      title_id: 'gt-002',
      publisher: 'Velocity Studios',
      rights_basis: 'platform_program',
      commercial_status: 'approved',
      support_tier: 'supported',
    },
    requirements: {
      gpu: 'NVIDIA RTX 3070 or higher',
      min_vram_gb: 8,
      encoder_required: 'NVENC H.264',
      recommended_downlink_mbps: 25,
    },
  },
  {
    id: 'gt-003',
    title: 'Iron Vanguard',
    genre: 'Tactical Shooter',
    cover_url: 'https://images.unsplash.com/photo-1542751371-adc38448a05e?w=400&h=600&fit=crop',
    description:
      'Lead a five-operator squad through procedural missions in a near-future conflict zone. Coordinate breaches, manage intel, and execute with precision — every round counts.',
    featured: false,
    active_hosts_count: 4,
    approval: {
      title_id: 'gt-003',
      publisher: 'Blacksite Games',
      rights_basis: 'internal_demo_only',
      commercial_status: 'conditional',
      support_tier: 'experimental',
    },
    requirements: {
      gpu: 'NVIDIA RTX 4080 or higher',
      min_vram_gb: 12,
      encoder_required: 'NVENC AV1',
      recommended_downlink_mbps: 40,
    },
  },
];

// ---------------------------------------------------------------------------
// Mock provider nodes — 3 nodes
// ---------------------------------------------------------------------------

export const MOCK_NODES: ProviderNode[] = [
  {
    node_id: 'node-us-east-01',
    name: 'US-East Primary',
    state: 'online_idle',
    region: 'us-east-1',
    ping_ms: 18,
    host_class: 'dedicated_test_machine',
    last_heartbeat_at: new Date(Date.now() - 4_000).toISOString(),
    telemetry: {
      gpu_name: 'NVIDIA GeForce RTX 4090',
      driver_version: '560.94',
      gpu_utilization_pct: 12,
      vram_used_gb: 3.2,
      vram_total_gb: 24,
      temp_celsius: 42,
      power_draw_watts: 85,
      fan_speed_pct: 30,
    },
  },
  {
    node_id: 'node-eu-west-01',
    name: 'EU-West Frankfurt',
    state: 'streaming',
    region: 'eu-west-1',
    ping_ms: 34,
    host_class: 'managed_fleet',
    last_heartbeat_at: new Date(Date.now() - 2_000).toISOString(),
    telemetry: {
      gpu_name: 'NVIDIA GeForce RTX 3080',
      driver_version: '555.85',
      gpu_utilization_pct: 78,
      vram_used_gb: 7.4,
      vram_total_gb: 10,
      temp_celsius: 71,
      power_draw_watts: 285,
      fan_speed_pct: 68,
    },
  },
  {
    node_id: 'node-ap-south-01',
    name: 'AP-South Mumbai',
    state: 'online_idle',
    region: 'ap-south-1',
    ping_ms: 52,
    host_class: 'trusted_partner',
    last_heartbeat_at: new Date(Date.now() - 8_000).toISOString(),
    telemetry: {
      gpu_name: 'NVIDIA GeForce RTX 4080',
      driver_version: '560.94',
      gpu_utilization_pct: 5,
      vram_used_gb: 1.8,
      vram_total_gb: 16,
      temp_celsius: 38,
      power_draw_watts: 62,
      fan_speed_pct: 25,
    },
  },
];

// ---------------------------------------------------------------------------
// Health check — tries the real orchestrator, falls back to mock
// ---------------------------------------------------------------------------

export async function checkOrchestratorHealth(): Promise<HealthCheckResponse> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2_000);
    const res = await fetch('http://localhost:8000/health', {
      signal: controller.signal,
    });
    clearTimeout(timeout);
    return (await res.json()) as HealthCheckResponse;
  } catch {
    return { status: 'unreachable', db: 'mock', version: '0.1.0-mock' };
  }
}

// ---------------------------------------------------------------------------
// Preflight check — simulated with Promise.withResolvers
// ---------------------------------------------------------------------------

export async function runPreflightCheck(): Promise<PreflightResult> {
  const { promise, resolve } = Promise.withResolvers<PreflightResult>();

  setTimeout(() => {
    resolve({
      rtt_ms: Math.round(24 + Math.random() * 18),
      jitter_ms: Number((2.1 + Math.random() * 4).toFixed(1)),
      packet_loss_pct: Number((Math.random() * 0.3).toFixed(2)),
      estimated_bandwidth_mbps: Math.round(45 + Math.random() * 55),
      connection_type: Math.random() > 0.3 ? 'direct_p2p' : 'turn_relay',
      passed: true,
      reasons: [],
    });
  }, 800);

  return promise;
}

// ---------------------------------------------------------------------------
// Session state machine — walks states on an interval
// ---------------------------------------------------------------------------

const SESSION_STATES: SessionState[] = [
  'requested',
  'eligibility_checked',
  'offered',
  'accepted',
  'reserved',
  'launching',
  'signaling',
  'connecting',
  'live',
];

export function subscribeSessionStateMachine(
  callback: (state: SessionState) => void,
): () => void {
  callback(SESSION_STATES[0]);
  let index = 1;

  const intervalId = setInterval(() => {
    if (index < SESSION_STATES.length) {
      callback(SESSION_STATES[index]);
      index++;
    } else {
      clearInterval(intervalId);
    }
  }, 550);

  return () => {
    clearInterval(intervalId);
  };
}
