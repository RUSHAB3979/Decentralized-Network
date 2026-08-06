# Safe Architecture for Renting AAA Games (Cloud PC Rental)

## Overview
Provide users with a remote Windows PC (bare‑metal or GPU‑passthrough VM) that they can log into with their **own Steam account** via Steam’s QR/device‑code flow. All game licenses remain on the user’s account; you never supply, copy, or redistribute game binaries. This mirrors lending a physical gaming rig to a friend and avoids violating Steam’s Subscriber Agreement, anti‑circumvention laws, and publisher EULAs.

---

## Core Principles
1. **Never see or store user credentials** – use Steam OAuth device flow / QR login.
2. **Never copy or share game files** – each user’s library stays on their own Steam account.
3. **Never attempt to defeat DRM or anti‑cheat** – provide clean hardware with stable identifiers.
4. **Ephemeral sessions** – wipe all user‑specific data after each rental.
5. **Operator accountability** – KYC + slashable bond for hardware providers.

---

## Authentication Flow
1. Front‑end shows “Sign in with Steam” button (Steam device flow or QR code).
2. User completes login on Steam’s official servers (mobile app or browser).
3. Your backend receives an **OAuth access token** (limited scope: `identity`, `profile`).
4. Using the token, retrieve the user’s SteamID to verify ownership.
5. Allocate a Windows node and launch Steam Big Picture.
6. Inside the remote PC, the user sees a Steam “Sign in with Steam” prompt; they scan the QR code shown on the remote screen with their phone (or use device‑code on another device).  
   → Password and Steam Guard code never touch your servers.
7. On session end: revoke the OAuth token, force Windows logout, wipe temporary volume.

*References*  
- Steam Web OAuth (device flow): https://partner.steamgames.com/doc/webapi/oauth  
- Steam QR login help: https://help.steampowered.com/en/wizard/HelpWithSteamQR  
- Revoking OAuth tokens: https://partner.steamgames.com/doc/webapi/oauth#revoking

---

## Hardware & Isolation
- **Bare‑metal GPU server** or **VM with full GPU passthrough (VFIO/pci)** – no hypervisor CPUID bit, no emulated devices.
- **Static hardware identifiers** – SMBIOS UUID, MAC address, serial number remain unchanged between sessions (no randomization).
- **Clean Windows image** – Windows 10/11 LTSC, signed GPU drivers, Steam client, no extra software, no telemetry opt‑outs beyond defaults.
- **Anti‑cheat safe** – No unsigned code, no debugging tools, no VM artefacts. If needed, engage anti‑cheat vendors (Riot, Easy Anti‑Cheat, BattlEye) to whitelist your hardware IDs as a trusted cloud‑gaming platform.
- **GPU assignment** – One physical GPU per tenant (no vGPU time‑slicing) to avoid driver instability and detection.

*References*  
- VFIO/GPU passthrough: https://wiki.archlinux.org/title/PCI_passthrough_via_VFIO  
- Steam hardware survey: https://store.steampowered.com/hwsurvey  
- NVIDIA Cloud Gaming whitepaper: https://www.nvidia.com/en-us/data-center/gpu-accelerated-applications/cloud-gaming/

---

## Session Management & Hygiene
1. **Node allocation** – Pull a pre‑imaged Windows node from a pool or boot via PXE/iPXE.
2. **Base image** – Contains Windows, GPU drivers, Steam client; launched with a startup task that starts Steam Big Picture and waits for user login.
3. **Ephemeral storage** – All user‑specific data (Steam cache, game updates, settings) stored on a temporary per‑session volume destroyed on session end.
4. **Logout & revocation** –  
   - Revoke the OAuth token obtained at login.  
   - Force logout of the local Windows account.  
   - Wipe pagefile, temporary files, and the session volume.  
   - Return node to the pool.
5. **Audit logs** – Store only hashed SteamID, node ID, timestamps, and session duration. Never store passwords, tokens, or game titles played.

---

## Legal & Compliance Checklist
| Area | Why OK | What to Verify |
|------|--------|----------------|
| **Steam Subscriber Agreement** | No credential storage or sharing; user is sole concurrent license holder. | Verify you never collect passwords or `ssfn`. |
| **Anti‑circumvention (India §65A, US DMCA §1201, EU Art. 6)** | No modification, bypass, or emulation of any DRM component; hardware presents genuine, stable identifiers. | Confirm no VM flags, no SMBIOS/CPU ID spoofing, no ssfn injection. |
| **Publisher EULAs** | User’s own account runs the game; you merely provide hardware (like a PC‑rental shop). | Maintain a blocklist of titles that explicitly forbid third‑party hosting (rare); either block streaming those titles or allow only local play. |
| **Data protection** | Only hashed SteamID stored; no personal data retained. | Ensure GDPR‑compliant deletion on request. |
| **Insurance / liability** | ToS state user responsible for own account conduct; hardware provided “as is”. | Include standard waiver, indemnity, and operator KYC/AML clauses. |

*References*  
- Steam Subscriber Agreement: https://store.steampowered.com/subscriber_agreement/  
- India Copyright Act §65A: https://www.indiacode.nic.in/handle/123456789/1736?view_type=browse&search=search�¤ty=&sorton=&query+=Section+65A  
- US DMCA §1201: https://www.copyright.gov/dmca/1201/  
- EU InfoSoc Directive Art. 6: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32001L0029

---

## Typical User Flow
1. User clicks **Start Gaming Session** on your website/app.  
2. System allocates a bare‑metal GPU node (or dedicated GPU‑passthrough VM) and boots the clean Windows image.  
3. Browser shows a QR code (or device‑code) with text: “Scan to log into Steam on your remote PC”.  
4. User opens Steam mobile app, taps **Scan QR code**, scans the code displayed on the remote PC’s screen (served by a simple HTML page on the node).  
5. Steam on the remote PC logs in, downloads pending updates, and presents the user’s library in Big Picture mode.  
6. User selects a game, clicks **Play**; game runs on the remote GPU, Steam Remote Play encodes video and sends it to the user’s local device (phone, tablet, laptop, TV).  
7. When finished, user hits **End Session** in your portal. Your backend:  
   - Revokes the OAuth token.  
   - Forces Windows logout.  
   - Wipes the temporary volume.  
   - Returns node to the pool.  

No passwords, no credential storage, no hardware spoofing, no game‑file sharing – just a legitimate remote Windows PC the user logs into with their own Steam account.

---

## What **NOT** to Do (Risky Paths to Avoid)
- **SSFN injection / hardware‑ID spoofing** – violates Steam SSA and anti‑circumvention laws; builds a credential honeypot.  
- **Steam Family Sharing / burner account** – a stolen burner token can be used to cheat in VAC‑protected shared titles, propagating a ban to the victim’s main account.  
- **P2P distribution of game binaries** – direct copyright infringement (Napster model).  
- **Shared marketplace game accounts** – violates Steam SSA and invites publisher claims.  
- **Nested VMs or over‑subscribed GPUs** – triggers VM detection, causes unstable driver state, risks blacklisting by anti‑cheat.  
- **Storing or replaying user credentials** – breaches Steam SSA §1.D and exposes you to liability.

---

## Next Steps (Implementation)
1. **Update matching/service logic** – add shard, `antiCheat`, and `drm` as hard filters (as previously reviewed).  
2. **Implement title‑sharded storage** for F2P, indie, and compute images (orchestrator‑dictated, demand‑driven provisioning).  
3. **Build auth micro‑service** – Node/Express (or similar) handling Steam device flow, token storage (short‑lived), and node‑allocation triggers (e.g., via Proxmox, vSphere, or bare‑metal API).  
4. **Create Windows base image** – with Steam client, GPU drivers, startup task launching Steam Big Picture.  
5. **Set up node pool** – automate provisioning, snapshotting, and wiping via your orchestration layer (e.g., Terraform + Ansible, or custom scripts).  
6. **Add operator onboarding** – KYC collection, bond escrow (smart contract or traditional legal agreement).  
7. **Pilot test** – run a single node with volunteer friends; verify login flow, hardware fingerprint stability, anti‑cheat/Denuvo behaviour, latency, and logout/wipe.  
8. **Iterate & scale** – add monitoring, alerting, and automated scaling based on city demand (title sharding concept).  

With these pieces in place, you have a technically solid, legally defensible service for renting out hardware to play AAA games. Feel free to ask for concrete code skeletons (auth endpoint, node‑provisioning script, or matching.ts changes) – I’m happy to draft them.
