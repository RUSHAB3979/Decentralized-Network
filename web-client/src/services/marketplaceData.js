export const WORKLOAD_PRODUCTS = [
  {
    id: 'render',
    eyebrow: 'Available in prototype',
    title: 'Render & media',
    description: 'Upload Blender projects and media jobs, choose a GPU profile, and collect validated artifacts.',
    accent: 'cyan',
    route: '/app/render',
    action: 'Create render job',
  },
  {
    id: 'models',
    eyebrow: 'Next product track',
    title: 'Model APIs',
    description: 'Call approved open-source models through one metered, OpenAI-compatible gateway.',
    accent: 'violet',
    route: '/app/models',
    action: 'Explore model APIs',
  },
  {
    id: 'workstations',
    eyebrow: 'Planned',
    title: 'GPU workstations',
    description: 'Reserve an ephemeral remote workstation for Blender, Unreal Engine, and creative applications.',
    accent: 'amber',
    route: '/app/workstations',
    action: 'View workstations',
  },
  {
    id: 'gaming',
    eyebrow: 'Permission gated',
    title: 'Cloud gaming',
    description: 'Low-latency interactive sessions for approved titles using the same verified GPU fabric.',
    accent: 'emerald',
    route: '/app/gaming',
    action: 'View gaming track',
  },
];

export const PREVIEW_GPU_OFFERS = [
  {
    id: 'offer-3060',
    gpu: 'RTX 3060',
    vram: '12 GB',
    region: 'Mumbai',
    rate: '$0.12/hr',
    fit: 'Blender · SDXL',
    availability: 'Preview offer',
  },
  {
    id: 'offer-4070ti',
    gpu: 'RTX 4070 Ti',
    vram: '16 GB',
    region: 'Bengaluru',
    rate: '$0.24/hr',
    fit: 'Cycles · Video AI',
    availability: 'Preview offer',
  },
  {
    id: 'offer-4090',
    gpu: 'RTX 4090',
    vram: '24 GB',
    region: 'Singapore',
    rate: '$0.46/hr',
    fit: 'LLMs · 4K render',
    availability: 'Preview offer',
  },
];

export const PREVIEW_JOBS = [
  {
    id: 'render_demo_01',
    name: 'Product animation · frames 1–120',
    type: 'Blender Cycles',
    status: 'completed',
    detail: 'Demo record · 120 artifacts',
  },
  {
    id: 'model_demo_02',
    name: 'Code model endpoint',
    type: 'Managed inference',
    status: 'planned',
    detail: 'Deployment workflow preview',
  },
];


