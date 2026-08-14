// ---------------------------------------------------------------------------
// Mock catalog — 3 titles
// ---------------------------------------------------------------------------
export const MOCK_CATALOG = [
    {
        id: 'gt-001',
        title: 'Stellar Odyssey',
        genre: 'Sci-Fi RPG',
        cover_url: 'https://images.unsplash.com/photo-1534996858221-380b92700493?w=400&h=600&fit=crop',
        description: 'Explore a vast procedurally-generated galaxy in this open-world sci-fi RPG. Command your starship, forge alliances with alien civilizations, and unravel an ancient mystery threatening the fabric of space-time.',
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
        description: 'Experience hyper-realistic motorsport with laser-scanned circuits, dynamic weather, and a full FIA-licensed championship season. Every tire compound, brake temperature, and aero setup matters.',
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
        description: 'Lead a five-operator squad through procedural missions in a near-future conflict zone. Coordinate breaches, manage intel, and execute with precision — every round counts.',
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
// MOCK_NODES lived here. It was three invented gaming hosts with fluctuating
// temperatures, and it was deleted in M1 rather than kept as a fallback -- see
// fetchProviderNodes() below for why a fallback would have been worse than
// nothing.
// ---------------------------------------------------------------------------
// Health check — tries the real orchestrator, falls back to mock
//
// Set VITE_ORCHESTRATOR_URL in web-client/.env.local to point at a running
// backend. The default matches ORCHESTRATOR_URL in the repo .env.example; the
// TypeScript orchestrator listens on 8080 and uvicorn defaults to 8000, so the
// port is configuration rather than a constant.
// ---------------------------------------------------------------------------
// Where the orchestrator lives, resolved in three steps.
//
// An explicit VITE_ORCHESTRATOR_URL always wins -- that is how you point a build
// at a staging backend, or at a colleague's machine.
//
// Otherwise it depends on where this page is being served from, because the
// answer genuinely differs. Running `npm run dev` on your laptop, the backend is
// on your laptop. Served from a deployed origin, it is the deployed backend --
// and hardcoding localhost there produced a site whose every request was blocked
// as mixed content before it left the browser, with the honest but unhelpful
// message "Cannot reach the orchestrator" for every visitor.
//
// The hosted URL is not a secret: it is a public API endpoint that appears in
// every request this bundle makes. Committing it is correct, and .env files are
// gitignored precisely so that things which *are* secret cannot follow it here.
const HOSTED_ORCHESTRATOR_URL = 'https://decentralized-network.onrender.com';

const isLocal = typeof window !== 'undefined'
    && ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname);

export const ORCHESTRATOR_URL =
    import.meta.env.VITE_ORCHESTRATOR_URL
    ?? (isLocal ? 'http://localhost:8080' : HOSTED_ORCHESTRATOR_URL);

export async function checkOrchestratorHealth() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);
    try {
        const res = await fetch(`${ORCHESTRATOR_URL}/health`, {
            signal: controller.signal,
        });
        // A 503 still carries a meaningful body ({status:'degraded', db:'down'}),
        // so parse it rather than discarding it as a transport failure.
        return (await res.json());
    }
    catch {
        return { status: 'unreachable', db: 'mock', version: '0.1.0-mock' };
    }
    finally {
        clearTimeout(timeout);
    }
}
// ---------------------------------------------------------------------------
// Provider nodes — real data from the orchestrator, or an explicit failure
//
// Note the difference from checkOrchestratorHealth above, which falls back to a
// mock object. That is fine for a status pill: 'unreachable' is visibly not a
// real health result. It is not fine here.
//
// If this returned an empty array when the request failed, the page would show
// "0 providers online" — a confident, specific, wrong answer that is
// indistinguishable from a genuinely empty marketplace. Nothing would throw and
// nobody would investigate. So the failure is returned as a value the caller is
// forced to handle, and the UI renders "cannot reach the orchestrator" instead
// of inventing a fleet size.
//
// The same reasoning is why the mock nodes were deleted rather than kept as a
// fallback: a marketplace that displays three fictional RTX 4090s when the
// backend is down is worse than one that displays an error.
// ---------------------------------------------------------------------------
export async function fetchProviderNodes({ timeoutMs = 5000 } = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(`${ORCHESTRATOR_URL}/providers/nodes`, {
            signal: controller.signal,
        });
        if (!res.ok) {
            // 503 means the orchestrator is up but its registry is not. That
            // is a different problem from an unreachable orchestrator, and
            // whoever is debugging needs to be told which one it is.
            const detail = await res.text().catch(() => '');
            return {
                ok: false,
                error: res.status === 503
                    ? 'The orchestrator cannot reach the provider registry.'
                    : `Orchestrator returned ${res.status}.`,
                detail,
            };
        }
        const body = await res.json();
        return {
            ok: true,
            nodes: body.nodes ?? [],
            ttlSeconds: body.ttl_seconds ?? null,
            serverTime: body.server_time ?? null,
        };
    }
    catch (err) {
        return {
            ok: false,
            error: err?.name === 'AbortError'
                ? `No response from the orchestrator within ${timeoutMs}ms.`
                : 'Cannot reach the orchestrator.',
            detail: String(err?.message ?? err),
        };
    }
    finally {
        clearTimeout(timeout);
    }
}
// ---------------------------------------------------------------------------
// Preflight check — simulated with Promise.withResolvers
// ---------------------------------------------------------------------------
export async function runPreflightCheck() {
    const { promise, resolve } = Promise.withResolvers();
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
const SESSION_STATES = [
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
export function subscribeSessionStateMachine(callback) {
    callback(SESSION_STATES[0]);
    let index = 1;
    const intervalId = setInterval(() => {
        if (index < SESSION_STATES.length) {
            callback(SESSION_STATES[index]);
            index++;
        }
        else {
            clearInterval(intervalId);
        }
    }, 550);
    return () => {
        clearInterval(intervalId);
    };
}
