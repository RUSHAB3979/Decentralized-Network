// Shared polling of the orchestrator's node registry.
//
// Extracted because two surfaces need the same data and must never disagree
// about it: the overview tab counts nodes, the nodes tab lists them. Two
// independent fetches would drift out of step and show, for instance, "3
// enrolled" above a table containing four rows — a discrepancy a user reads as
// "this dashboard is broken", with nothing raising anywhere.
//
// It also keeps the failure semantics in one place. `status` is a state
// machine, not a boolean: 'loading' and 'error' are distinct from an empty
// fleet, because an empty fleet is a real and meaningful answer that must not
// be produced by a failed request.
import { useState, useEffect, useCallback } from 'react';
import { fetchProviderNodes } from '../services/api';

export const NODE_POLL_MS = 5000;

export function useProviderNodes(pollMs = NODE_POLL_MS) {
    const [result, setResult] = useState({ status: 'loading', nodes: [] });

    const load = useCallback(async () => {
        const response = await fetchProviderNodes();
        setResult(response.ok
            ? {
                status: 'ok',
                nodes: response.nodes,
                ttlSeconds: response.ttlSeconds,
                serverTime: response.serverTime,
            }
            : {
                status: 'error',
                nodes: [],
                error: response.error,
                detail: response.detail,
            });
    }, []);

    useEffect(() => {
        let cancelled = false;
        const tick = () => {
            // Polling from a hidden tab spends the user's bandwidth and our
            // request budget on a view nobody is looking at.
            if (!document.hidden && !cancelled)
                load();
        };
        tick();
        const id = setInterval(tick, pollMs);
        return () => { cancelled = true; clearInterval(id); };
    }, [load, pollMs]);

    return result;
}

// Derived counts, defined once so every surface agrees on what "online" and
// "available" mean. `available` deliberately requires both liveness and the
// node's own consent: a provider who has switched to draining is online and
// must not be counted as capacity.
export function summarise(nodes) {
    const online = nodes.filter((n) => n.liveness === 'online');
    return {
        enrolled: nodes.length,
        online: online.length,
        available: online.filter((n) => n.accepts_work).length,
    };
}
