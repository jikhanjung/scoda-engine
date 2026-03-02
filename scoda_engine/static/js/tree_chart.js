/**
 * SCODA Desktop — Tree Chart View (Radial + Rectangular)
 * D3-based tree visualization for hierarchy data.
 * Supports two layout modes: radial (concentric) and rectangular (cladogram).
 * Lazy-loads D3.js only when this view is activated.
 */

// D3 lazy load state
let d3Ready = null;

// Tree chart view state (internal variable names kept as radial* for minimal refactoring)
let radialRoot = null;
let radialFullRoot = null;   // Full tree (with leaf rank)
let radialPrunedRoot = null; // Pruned tree (leaf rank removed)
let radialSubtreeNode = null; // Current subtree root (null = whole tree)
let radialViewDef = null;
let radialViewKey = null;
let radialTransform = null;
let radialQuadtree = null;
let radialColorMap = {};
let radialFocusNode = null;
let radialDepthHidden = false;
let radialSearchMatches = [];
let radialCanvas = null;
let radialCtx = null;
let radialLabelsSvg = null;
let radialZoom = null;
let radialDpr = 1;
let radialWidth = 0;
let radialHeight = 0;
let radialOuterRadius = 0;

// Layout mode state
let treeLayoutMode = 'radial';  // 'radial' or 'rectangular'
let cladoBoundsW = 0;
let cladoBoundsH = 0;

// --- D3 Lazy Loading ---

function ensureD3Loaded() {
    if (d3Ready) return d3Ready;
    d3Ready = new Promise((resolve, reject) => {
        if (window.d3) return resolve();
        const script = document.createElement('script');
        script.src = 'https://d3js.org/d3.v7.min.js';
        script.onload = resolve;
        script.onerror = () => reject(new Error('Failed to load D3.js'));
        document.head.appendChild(script);
    });
    return d3Ready;
}

// --- Main Entry Point ---

async function loadRadialView(viewKey) {
    const wrap = document.getElementById('tc-canvas-wrap');
    wrap.innerHTML = '<div class="loading">Loading D3.js...</div>';

    try {
        await ensureD3Loaded();
    } catch (e) {
        wrap.innerHTML = '<div class="text-danger">Failed to load D3.js. Check your internet connection.</div>';
        return;
    }

    // Restore canvas + SVG structure
    wrap.innerHTML = '<canvas id="tc-canvas"></canvas><svg id="tc-labels"></svg>';

    const view = manifest.views[viewKey];
    if (!view) return;

    radialViewDef = view;
    radialViewKey = viewKey;
    radialDepthHidden = true;  // Start with pruned tree (Family level)
    radialSearchMatches = [];
    radialFocusNode = null;
    radialSubtreeNode = null;

    // Read layout mode from tree_chart_options
    const tcOpts = view.tree_chart_options || {};
    treeLayoutMode = tcOpts.default_layout || 'radial';

    // Setup canvas
    radialCanvas = document.getElementById('tc-canvas');
    radialCtx = radialCanvas.getContext('2d');
    radialLabelsSvg = d3.select('#tc-labels');
    radialDpr = window.devicePixelRatio || 1;

    resizeRadialCanvas();

    // Build toolbar
    buildRadialToolbar(view);

    // Fetch data and build hierarchy (builds both full and pruned trees)
    try {
        await buildRadialHierarchy(view);
    } catch (e) {
        wrap.innerHTML = `<div class="text-danger">Error loading data: ${e.message}</div>`;
        return;
    }

    // Start with pruned tree if available, otherwise full
    radialRoot = radialPrunedRoot || radialFullRoot;
    if (!radialRoot) {
        wrap.innerHTML = '<div class="text-muted" style="padding:20px;text-align:center;">No hierarchy data found.</div>';
        return;
    }

    // Compute layout
    computeLayout(radialRoot, view);

    // Assign colors
    assignRadialColors(radialRoot, view);

    // Build quadtree for hover
    buildRadialQuadtree(radialRoot);

    // Setup zoom
    setupRadialZoom();

    // Initial render — fit zoom if tree exceeds canvas
    radialTransform = computeFitTransform();
    d3.select(radialCanvas).call(radialZoom.transform, radialTransform);
    renderRadial();
    updateRadialBreadcrumb();
}

// --- Data Loading ---

async function buildRadialHierarchy(view) {
    const hOpts = view.hierarchy_options;
    const tcOpts = view.tree_chart_options || {};
    const rows = await fetchQuery(view.source_query);

    if (!rows || rows.length === 0) return null;

    // If edge_query is specified, load edges separately
    if (tcOpts.edge_query) {
        // Resolve $variable references in edge_params (e.g. "$profile_id" → globalControls value)
        const resolvedParams = {};
        for (const [k, v] of Object.entries(tcOpts.edge_params || {})) {
            resolvedParams[k] = (typeof v === 'string' && v.startsWith('$'))
                ? (globalControls[v.slice(1)] ?? v) : v;
        }
        const edges = await fetchQuery(tcOpts.edge_query, resolvedParams);
        console.log(`[tree_chart] edge_query="${tcOpts.edge_query}" returned ${edges.length} edges`);
        const childKey = tcOpts.edge_child_key || 'child_id';
        const parentKey = tcOpts.edge_parent_key || 'parent_id';
        if (edges.length > 0) {
            console.log(`[tree_chart] edge[0] keys:`, Object.keys(edges[0]), JSON.stringify(edges[0]));
        }
        // Use String keys to avoid number/string type mismatch between queries
        const parentMap = new Map(edges.map(e => [String(e[childKey]), e[parentKey]]));
        const edgeChildIds = new Set(edges.map(e => String(e[childKey])));
        rows.forEach(n => {
            const mapped = parentMap.get(String(n[hOpts.id_key]));
            n[hOpts.parent_key] = mapped !== undefined ? mapped : null;
        });

        // Remove orphan nodes (not part of the classification tree)
        const edgeParentIds = new Set(edges.map(e => String(e[parentKey])));
        const before = rows.length;
        const filtered = rows.filter(n => {
            const id = String(n[hOpts.id_key]);
            // Keep if: is a child in an edge, OR is a parent in an edge
            return edgeChildIds.has(id) || edgeParentIds.has(id);
        });
        rows.length = 0;
        rows.push(...filtered);
        console.log(`[tree_chart] filtered orphans: ${before} → ${rows.length} nodes`);
    } else {
        console.log('[tree_chart] no edge_query configured');
    }

    // If multiple roots, insert a virtual root so d3.stratify() works
    const idKey = hOpts.id_key;
    const parentKey = hOpts.parent_key;
    const roots = rows.filter(r => !r[parentKey]);
    console.log(`[tree_chart] ${rows.length} nodes, ${roots.length} root(s)`);
    if (roots.length > 1) {
        const virtualRoot = { [idKey]: '__virtual_root__', [parentKey]: null };
        virtualRoot[hOpts.label_key || 'name'] = '';
        virtualRoot[hOpts.rank_key || 'rank'] = '_root';
        rows.unshift(virtualRoot);
        roots.forEach(r => { r[parentKey] = '__virtual_root__'; });
    }

    const stratify = d3.stratify().id(d => d[idKey]).parentId(d => d[parentKey]);
    const labelKey = hOpts.label_key || 'name';
    const countKey = tcOpts.count_key || hOpts.count_key;
    const rankKey = hOpts.rank_key || 'rank';
    const leafRank = tcOpts.leaf_rank;

    function buildTree(data) {
        const tree = stratify(data);
        if (countKey) { tree.sum(d => d[countKey] || 0); } else { tree.count(); }
        // Sort: non-leaf ranks first (alphabetically), then leaf rank (alphabetically)
        tree.sort((a, b) => {
            const aIsLeaf = leafRank && a.data[rankKey] === leafRank;
            const bIsLeaf = leafRank && b.data[rankKey] === leafRank;
            if (aIsLeaf !== bIsLeaf) return aIsLeaf ? 1 : -1;
            return (a.data[labelKey] || '').localeCompare(b.data[labelKey] || '');
        });
        return tree;
    }

    // Full tree (all nodes)
    radialFullRoot = buildTree(rows);

    // Pruned tree (leaf rank removed) — for depth toggle
    if (leafRank) {
        const prunedRows = rows.filter(r => r[rankKey] !== leafRank);
        if (prunedRows.length > 0) {
            radialPrunedRoot = buildTree(prunedRows);
        }
    }

    return radialFullRoot;
}

// --- Layout Dispatcher ---

function computeLayout(root, view) {
    if (treeLayoutMode === 'rectangular') {
        computeCladogramLayout(root, view);
    } else {
        computeRadialLayout(root, view);
    }
}

// --- Radial Layout ---

function computeRadialLayout(root, view) {
    const tcOpts = view.tree_chart_options || {};
    const rankKey = view.hierarchy_options.rank_key || 'rank';
    radialOuterRadius = Math.min(radialWidth, radialHeight) * 0.42;

    // Bottom-up angular layout: assign angles to leaves first,
    // then center parents among children — same approach as rectangular
    // to guarantee no overlap.
    const LEAF_GAP_DEG = 2;        // minimum angular gap between leaves (degrees)
    const SUBTREE_GAP_DEG = 1;     // extra gap between sibling subtrees
    let nextAngle = 0;

    function layoutRadialSubtree(node) {
        if (!node.children || node.children.length === 0) {
            node._la = nextAngle;
            nextAngle += node._children ? LEAF_GAP_DEG * 2 : LEAF_GAP_DEG;
            return;
        }
        for (let i = 0; i < node.children.length; i++) {
            layoutRadialSubtree(node.children[i]);
            if (i < node.children.length - 1) {
                nextAngle += SUBTREE_GAP_DEG;
            }
        }
        const first = node.children[0];
        const last = node.children[node.children.length - 1];
        node._la = (first._la + last._la) / 2;
    }

    layoutRadialSubtree(root);

    // Scale angles to fill 360 degrees
    const totalAngle = nextAngle || 1;
    root.each(node => {
        node.x = (node._la / totalAngle) * 360;
        node.y = node.depth * (radialOuterRadius / (root.height || 1));
    });

    // --- Dynamic radius: ensure minimum arc spacing between adjacent leaves ---
    const MIN_SPACING = 20; // minimum arc distance in pixels
    const leaves = [];
    root.each(d => {
        if (!d.children && !d._children) leaves.push(d);
    });

    if (leaves.length >= 2) {
        leaves.sort((a, b) => a.x - b.x);
        let minDeltaTheta = Infinity;
        for (let i = 1; i < leaves.length; i++) {
            const delta = leaves[i].x - leaves[i - 1].x;
            if (delta > 0 && delta < minDeltaTheta) minDeltaTheta = delta;
        }
        const wrapDelta = 360 - leaves[leaves.length - 1].x + leaves[0].x;
        if (wrapDelta > 0 && wrapDelta < minDeltaTheta) minDeltaTheta = wrapDelta;

        if (minDeltaTheta > 0 && minDeltaTheta < Infinity) {
            const minDeltaRad = minDeltaTheta * Math.PI / 180;
            const minArc = radialOuterRadius * minDeltaRad;
            if (minArc < MIN_SPACING) {
                const scaleFactor = MIN_SPACING / minArc;
                radialOuterRadius *= scaleFactor;
                root.each(d => { d.y *= scaleFactor; });
            }
        }
    }

    // Override radii by rank if specified
    const rankRadius = tcOpts.rank_radius;
    if (rankRadius) {
        root.each(node => {
            const rank = node.data[rankKey];
            if (rank && rankRadius[rank] !== undefined) {
                node.y = rankRadius[rank] * radialOuterRadius;
            }
        });
    }

    // Store cartesian coordinates for each node
    root.each(node => {
        const angle = (node.x - 90) * Math.PI / 180;
        node.cx = node.y * Math.cos(angle);
        node.cy = node.y * Math.sin(angle);
    });
}

// --- Rectangular (Cladogram) Layout ---

function computeCladogramLayout(root, view) {
    const tcOpts = view.tree_chart_options || {};
    const rankKey = view.hierarchy_options.rank_key || 'rank';

    const LEAF_GAP = 24;       // minimum vertical gap between adjacent leaves
    const SUBTREE_GAP = 8;     // extra gap between sibling subtrees

    // Bottom-up layout: leaves first, then center parents among children.
    // This guarantees no overlap because every leaf gets a unique Y slot.
    let nextY = 0;

    function layoutSubtree(node) {
        if (!node.children || node.children.length === 0) {
            // Leaf or collapsed node
            node._ly = nextY;
            nextY += node._children ? LEAF_GAP * 2 : LEAF_GAP;
            return;
        }
        for (let i = 0; i < node.children.length; i++) {
            layoutSubtree(node.children[i]);
            if (i < node.children.length - 1) {
                nextY += SUBTREE_GAP;
            }
        }
        // Center among children
        const first = node.children[0];
        const last = node.children[node.children.length - 1];
        node._ly = (first._ly + last._ly) / 2;
    }

    layoutSubtree(root);

    const treeH = Math.max(nextY, LEAF_GAP);
    const maxDepth = root.height || 1;
    const depthSpacing = 120;
    const treeW = maxDepth * depthSpacing;

    // Assign positions: x = vertical (from _ly), y = horizontal (from depth)
    root.each(node => {
        node.x = node._ly;
        node.y = node.depth * depthSpacing;
    });

    // Align same-rank nodes to the same X position
    const rankRadius = tcOpts.rank_radius;
    if (rankRadius) {
        root.each(node => {
            const rank = node.data[rankKey];
            if (rank && rankRadius[rank] !== undefined) {
                node.y = rankRadius[rank] * treeW;
            }
        });
    } else {
        // Auto-compute: group by rank, average depth → snap to same position
        const rankSum = {};
        const rankCount = {};
        root.each(node => {
            if (isNodeHidden(node)) return;
            const rank = node.data[rankKey];
            if (!rank) return;
            rankSum[rank] = (rankSum[rank] || 0) + node.depth;
            rankCount[rank] = (rankCount[rank] || 0) + 1;
        });
        const ranks = Object.keys(rankSum)
            .sort((a, b) => (rankSum[a] / rankCount[a]) - (rankSum[b] / rankCount[b]));
        const rankY = {};
        ranks.forEach((rank, i) => {
            rankY[rank] = (ranks.length > 1) ? (i / (ranks.length - 1)) * treeW : 0;
        });
        root.each(node => {
            const rank = node.data[rankKey];
            if (rank && rankY[rank] !== undefined) {
                node.y = rankY[rank];
            }
        });
    }

    cladoBoundsW = treeW;
    cladoBoundsH = treeH;

    // d3 tree: node.x = vertical spread [0, treeH], node.y = depth [0, treeW]
    // Map to centered cartesian (left-to-right tree)
    root.each(node => {
        node.cx = node.y - treeW / 2;   // depth → horizontal
        node.cy = node.x - treeH / 2;   // spread → vertical
    });
}

// --- Fit Transform ---

function computeFitTransform() {
    if (treeLayoutMode === 'rectangular') {
        const padding = 120; // extra room for labels on the right
        const scaleX = radialWidth / (cladoBoundsW + padding);
        const scaleY = radialHeight / (cladoBoundsH + padding);
        const fitScale = Math.min(scaleX, scaleY);
        if (fitScale < 1) return d3.zoomIdentity.scale(fitScale);
        return d3.zoomIdentity;
    }
    // Radial mode
    const padding = 40;
    const fitScale = Math.min(radialWidth, radialHeight) / (2 * radialOuterRadius + padding);
    if (fitScale < 1) {
        return d3.zoomIdentity.scale(fitScale);
    }
    return d3.zoomIdentity;
}

// --- Colors ---

function assignRadialColors(root, view) {
    const tcOpts = view.tree_chart_options || {};
    const colorKey = tcOpts.color_key;
    radialColorMap = {};

    // Get top-level children for color assignment
    const topChildren = root.children || [];
    const palette = d3.schemeTableau10;

    topChildren.forEach((child, i) => {
        const color = palette[i % palette.length];
        radialColorMap[child.id] = color;
        // Propagate to descendants
        child.each(d => {
            d._color = color;
        });
    });

    root._color = '#6c757d';

    // If color_key specified, use data field for grouping
    if (colorKey) {
        const groups = new Set();
        root.each(d => {
            if (d.data[colorKey]) groups.add(d.data[colorKey]);
        });
        const groupArr = [...groups].sort();
        const groupColorMap = {};
        groupArr.forEach((g, i) => {
            groupColorMap[g] = palette[i % palette.length];
        });
        root.each(d => {
            if (d.data[colorKey]) {
                d._color = groupColorMap[d.data[colorKey]];
            }
        });
    }
}

// --- Quadtree ---

function buildRadialQuadtree(root) {
    const nodes = [];
    root.each(d => nodes.push(d));
    radialQuadtree = d3.quadtree()
        .x(d => d.cx)
        .y(d => d.cy)
        .addAll(nodes);
}

// --- Toolbar ---

function buildRadialToolbar(view) {
    const toolbar = document.getElementById('tc-toolbar');
    const tcOpts = view.tree_chart_options || {};
    let html = '';

    // Search
    html += '<input type="text" id="tc-search" placeholder="Search nodes..." autocomplete="off">';

    // Layout toggle
    const radialActive = treeLayoutMode === 'radial' ? ' active' : '';
    const rectActive = treeLayoutMode === 'rectangular' ? ' active' : '';
    html += `<button id="tc-layout-radial" class="tc-layout-btn${radialActive}" title="Radial layout"><i class="bi bi-bullseye"></i></button>`;
    html += `<button id="tc-layout-rect" class="tc-layout-btn${rectActive}" title="Rectangular layout"><i class="bi bi-diagram-3"></i></button>`;

    // Depth toggle (starts active = pruned)
    if (tcOpts.depth_toggle && tcOpts.leaf_rank) {
        html += `<button id="tc-depth-btn" class="active" title="Toggle leaf nodes">
                    <i class="bi bi-layers"></i> ${tcOpts.leaf_rank}
                 </button>`;
    }

    // Reset zoom
    html += '<button id="tc-reset-btn" title="Reset zoom"><i class="bi bi-arrows-fullscreen"></i></button>';

    toolbar.innerHTML = html;

    // Event: search
    const searchInput = document.getElementById('tc-search');
    if (searchInput) {
        let timer;
        searchInput.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(() => radialSearch(searchInput.value.trim()), 200);
        });
    }

    // Event: layout toggle
    const radialBtn = document.getElementById('tc-layout-radial');
    const rectBtn = document.getElementById('tc-layout-rect');
    if (radialBtn && rectBtn) {
        radialBtn.addEventListener('click', () => switchLayout('radial'));
        rectBtn.addEventListener('click', () => switchLayout('rectangular'));
    }

    // Event: depth toggle — switch between full and pruned tree
    const depthBtn = document.getElementById('tc-depth-btn');
    if (depthBtn) {
        depthBtn.addEventListener('click', () => {
            radialDepthHidden = !radialDepthHidden;
            depthBtn.classList.toggle('active', radialDepthHidden);
            // If viewing a subtree, rebuild from subtree node in the new source tree
            if (radialSubtreeNode) {
                navigateToSubtree(radialSubtreeNode.id);
            } else {
                radialRoot = radialDepthHidden && radialPrunedRoot ? radialPrunedRoot : radialFullRoot;
                computeLayout(radialRoot, radialViewDef);
                assignRadialColors(radialRoot, radialViewDef);
                buildRadialQuadtree(radialRoot);
                radialTransform = computeFitTransform();
                d3.select(radialCanvas).call(radialZoom.transform, radialTransform);
                renderRadial();
            }
        });
    }

    // Event: reset — back to full tree, reset zoom
    const resetBtn = document.getElementById('tc-reset-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            radialFocusNode = null;
            if (radialSubtreeNode) {
                clearSubtreeRoot();
            } else {
                d3.select(radialCanvas)
                    .transition().duration(500)
                    .call(radialZoom.transform, computeFitTransform());
            }
        });
    }
}

function switchLayout(mode) {
    if (mode === treeLayoutMode) return;
    treeLayoutMode = mode;

    // Update toolbar button active states
    const radialBtn = document.getElementById('tc-layout-radial');
    const rectBtn = document.getElementById('tc-layout-rect');
    if (radialBtn) radialBtn.classList.toggle('active', mode === 'radial');
    if (rectBtn) rectBtn.classList.toggle('active', mode === 'rectangular');

    // Recompute layout and re-render
    if (radialRoot) {
        computeLayout(radialRoot, radialViewDef);
        buildRadialQuadtree(radialRoot);
        radialTransform = computeFitTransform();
        d3.select(radialCanvas).call(radialZoom.transform, radialTransform);
        renderRadial();
    }
}

// --- Search ---

function radialSearch(term) {
    radialSearchMatches = [];
    if (!term || !radialRoot) {
        renderRadial();
        return;
    }

    const lower = term.toLowerCase();
    const labelKey = radialViewDef.hierarchy_options.label_key || 'name';

    radialRoot.each(d => {
        const label = (d.data[labelKey] || '').toLowerCase();
        if (label.includes(lower)) {
            radialSearchMatches.push(d);
        }
    });

    // Zoom to first match
    if (radialSearchMatches.length > 0) {
        const target = radialSearchMatches[0];
        zoomToNode(target, 4);
    }

    renderRadial();
}

// --- Zoom ---

function setupRadialZoom() {
    radialZoom = d3.zoom()
        .scaleExtent([0.3, 30])
        .on('zoom', (event) => {
            radialTransform = event.transform;
            renderRadial();
        });

    d3.select(radialCanvas)
        .call(radialZoom)
        .on('dblclick.zoom', null)
        .on('mousemove', onRadialMouseMove)
        .on('click', onRadialClick)
        .on('contextmenu', onRadialContextMenu);

    // Close context menu on click anywhere
    document.addEventListener('click', hideRadialContextMenu);
    document.addEventListener('contextmenu', (e) => {
        // Only close if not on the canvas (canvas handles its own)
        if (e.target !== radialCanvas) hideRadialContextMenu();
    });
}

function zoomToNode(node, scale) {
    if (!node || !radialZoom) return;
    scale = scale || 4;
    const cx = radialWidth / 2;
    const cy = radialHeight / 2;
    const transform = d3.zoomIdentity
        .translate(cx, cy)
        .scale(scale)
        .translate(-node.cx, -node.cy);

    d3.select(radialCanvas)
        .transition().duration(600)
        .call(radialZoom.transform, transform);
}

// --- Interaction: Mouse ---

function onRadialMouseMove(event) {
    if (!radialQuadtree || !radialTransform) return;

    const [mx, my] = d3.pointer(event, radialCanvas);
    const cx = radialWidth / 2;
    const cy = radialHeight / 2;

    // Invert transform to data coordinates
    const dx = (mx - radialTransform.x - cx * radialTransform.k) / radialTransform.k + cx;
    const dy = (my - radialTransform.y - cy * radialTransform.k) / radialTransform.k + cy;
    const dataX = dx - cx;
    const dataY = dy - cy;

    const searchRadius = 15 / radialTransform.k;
    const nearest = radialQuadtree.find(dataX, dataY, searchRadius);

    const tooltip = document.getElementById('tc-tooltip');
    if (nearest && !isNodeHidden(nearest)) {
        const labelKey = radialViewDef.hierarchy_options.label_key || 'name';
        const rankKey = radialViewDef.hierarchy_options.rank_key || 'rank';
        const tcOpts = radialViewDef.tree_chart_options || {};
        const countKey = tcOpts.count_key || radialViewDef.hierarchy_options.count_key;

        let html = `<div class="tc-tt-name">${nearest.data[labelKey] || nearest.id}</div>`;
        if (nearest.data[rankKey]) {
            html += `<div class="tc-tt-rank">${nearest.data[rankKey]}</div>`;
        }
        if (countKey && nearest.value !== undefined) {
            html += `<div class="tc-tt-count">${countKey}: ${nearest.value}</div>`;
        }

        tooltip.innerHTML = html;
        tooltip.style.display = '';
        tooltip.style.left = (mx + 12) + 'px';
        tooltip.style.top = (my - 10) + 'px';

        // Keep tooltip inside viewport
        const rect = tooltip.getBoundingClientRect();
        const wrap = document.getElementById('tc-canvas-wrap').getBoundingClientRect();
        if (rect.right > wrap.right) {
            tooltip.style.left = (mx - rect.width - 8) + 'px';
        }
        if (rect.bottom > wrap.bottom) {
            tooltip.style.top = (my - rect.height - 8) + 'px';
        }
    } else {
        tooltip.style.display = 'none';
    }
}

function onRadialClick(event) {
    if (!radialQuadtree || !radialTransform) return;

    const [mx, my] = d3.pointer(event, radialCanvas);
    const cx = radialWidth / 2;
    const cy = radialHeight / 2;

    const dx = (mx - radialTransform.x - cx * radialTransform.k) / radialTransform.k + cx;
    const dy = (my - radialTransform.y - cy * radialTransform.k) / radialTransform.k + cy;
    const dataX = dx - cx;
    const dataY = dy - cy;

    const searchRadius = 15 / radialTransform.k;
    const nearest = radialQuadtree.find(dataX, dataY, searchRadius);

    if (!nearest || isNodeHidden(nearest)) return;

    const tcOpts = radialViewDef.tree_chart_options || {};

    const isLeaf = isLeafByRank(nearest);

    // Leaf node → detail modal
    if (isLeaf) {
        if (tcOpts.on_node_click) {
            const idKey = tcOpts.on_node_click.id_key || tcOpts.on_node_click.id_field;
            const detailView = tcOpts.on_node_click.detail_view;
            if (detailView && idKey && nearest.data[idKey] && typeof openDetailModal === 'function') {
                openDetailModal(detailView, nearest.data[idKey]);
            }
        }
        return;
    }

    // Internal node → toggle collapse/expand
    toggleRadialNode(nearest);
}

function toggleRadialNode(node) {
    if (node._children) {
        // Expand: restore children
        node.children = node._children;
        node._children = null;
    } else if (node.children) {
        // Collapse: hide children
        node._children = node.children;
        node.children = null;
    } else {
        return; // leaf — nothing to toggle
    }

    // Recount after structure change
    const tcOpts = radialViewDef.tree_chart_options || {};
    const countKey = tcOpts.count_key || radialViewDef.hierarchy_options.count_key;
    if (countKey) {
        radialRoot.sum(d => d[countKey] || 0);
    } else {
        radialRoot.count();
    }

    // Recompute layout
    computeLayout(radialRoot, radialViewDef);
    assignRadialColors(radialRoot, radialViewDef);
    buildRadialQuadtree(radialRoot);
    renderRadial();
}

// --- Context Menu ---

let radialContextTarget = null;  // node that was right-clicked

function onRadialContextMenu(event) {
    event.preventDefault();
    if (!radialQuadtree || !radialTransform) return;

    const [mx, my] = d3.pointer(event, radialCanvas);
    const cx = radialWidth / 2;
    const cy = radialHeight / 2;

    const dx = (mx - radialTransform.x - cx * radialTransform.k) / radialTransform.k + cx;
    const dy = (my - radialTransform.y - cy * radialTransform.k) / radialTransform.k + cy;
    const dataX = dx - cx;
    const dataY = dy - cy;

    const searchRadius = 15 / radialTransform.k;
    const nearest = radialQuadtree.find(dataX, dataY, searchRadius);

    if (!nearest || isNodeHidden(nearest)) {
        hideRadialContextMenu();
        return;
    }

    radialContextTarget = nearest;
    showRadialContextMenu(event, nearest);
}

function showRadialContextMenu(event, node) {
    const menu = document.getElementById('tc-context-menu');
    if (!menu) return;

    // Hide tooltip
    const tooltip = document.getElementById('tc-tooltip');
    if (tooltip) tooltip.style.display = 'none';

    const labelKey = radialViewDef.hierarchy_options.label_key || 'name';
    const rankKey = radialViewDef.hierarchy_options.rank_key || 'rank';
    const label = node.data[labelKey] || node.id;
    const rank = node.data[rankKey] || '';
    const isLeaf = isLeafByRank(node);
    const hasChildren = node.children || node._children;

    let html = '';

    // Header: node name
    html += `<div style="padding:6px 14px;font-weight:600;font-size:0.8rem;color:#6c757d;border-bottom:1px solid #eee;">${rank ? rank + ': ' : ''}${label}</div>`;

    // "View as root" — only for internal nodes
    if (!isLeaf && hasChildren) {
        html += `<div class="tc-cm-item" onclick="rcmViewAsRoot()"><i class="bi bi-diagram-3"></i> View as root</div>`;
    }

    // "Expand / Collapse" — for internal nodes
    if (hasChildren) {
        if (node._children) {
            html += `<div class="tc-cm-item" onclick="rcmToggle()"><i class="bi bi-chevron-expand"></i> Expand</div>`;
        } else if (node.children) {
            html += `<div class="tc-cm-item" onclick="rcmToggle()"><i class="bi bi-chevron-contract"></i> Collapse</div>`;
        }
    }

    // "Zoom to" — always available
    html += `<div class="tc-cm-item" onclick="rcmZoomTo()"><i class="bi bi-search"></i> Zoom to</div>`;

    // "Detail" — for leaf nodes with detail_view configured
    const tcOpts = radialViewDef.tree_chart_options || {};
    if (isLeaf && tcOpts.on_node_click) {
        html += `<div class="tc-cm-item" onclick="rcmDetail()"><i class="bi bi-info-circle"></i> Detail</div>`;
    }

    menu.innerHTML = html;
    menu.style.display = 'block';

    // Position near the mouse, inside the canvas wrap
    const wrap = document.getElementById('tc-canvas-wrap');
    const wrapRect = wrap.getBoundingClientRect();
    let left = event.clientX - wrapRect.left;
    let top = event.clientY - wrapRect.top;

    menu.style.left = left + 'px';
    menu.style.top = top + 'px';

    // Keep inside viewport
    requestAnimationFrame(() => {
        const menuRect = menu.getBoundingClientRect();
        if (menuRect.right > wrapRect.right) {
            menu.style.left = (left - menuRect.width) + 'px';
        }
        if (menuRect.bottom > wrapRect.bottom) {
            menu.style.top = (top - menuRect.height) + 'px';
        }
    });
}

function hideRadialContextMenu() {
    const menu = document.getElementById('tc-context-menu');
    if (menu) menu.style.display = 'none';
    radialContextTarget = null;
}

function rcmViewAsRoot() {
    const node = radialContextTarget;
    hideRadialContextMenu();
    if (node) setSubtreeRoot(node);
}

function rcmToggle() {
    const node = radialContextTarget;
    hideRadialContextMenu();
    if (node) toggleRadialNode(node);
}

function rcmZoomTo() {
    const node = radialContextTarget;
    hideRadialContextMenu();
    if (node) zoomToNode(node, 4);
}

function rcmDetail() {
    const node = radialContextTarget;
    hideRadialContextMenu();
    if (!node) return;
    const tcOpts = radialViewDef.tree_chart_options || {};
    if (tcOpts.on_node_click) {
        const idKey = tcOpts.on_node_click.id_key || tcOpts.on_node_click.id_field;
        const detailView = tcOpts.on_node_click.detail_view;
        if (detailView && idKey && node.data[idKey] && typeof openDetailModal === 'function') {
            openDetailModal(detailView, node.data[idKey]);
        }
    }
}

function setSubtreeRoot(node) {
    if (!node) return;

    // Find the matching node in the appropriate source tree
    const sourceTree = radialDepthHidden && radialPrunedRoot ? radialPrunedRoot : radialFullRoot;

    // If already viewing this subtree, go back up
    if (radialSubtreeNode && radialSubtreeNode.id === node.id) {
        // Go up to parent subtree, or back to full tree
        if (radialSubtreeNode.parent && !isNodeHidden(radialSubtreeNode.parent)) {
            navigateToSubtree(radialSubtreeNode.parent.id);
        } else {
            clearSubtreeRoot();
        }
        return;
    }

    navigateToSubtree(node.id);
}

function navigateToSubtree(nodeId) {
    const sourceTree = radialDepthHidden && radialPrunedRoot ? radialPrunedRoot : radialFullRoot;

    // Find node in source tree
    let targetNode = null;
    sourceTree.each(d => { if (d.id === nodeId) targetNode = d; });
    if (!targetNode || isLeafByRank(targetNode)) return;

    radialSubtreeNode = targetNode;

    // Build a subtree copy using d3.hierarchy from this node's descendants
    const subtreeRoot = buildSubtreeFromNode(targetNode);
    if (!subtreeRoot) return;

    radialRoot = subtreeRoot;
    computeLayout(radialRoot, radialViewDef);
    assignRadialColors(radialRoot, radialViewDef);
    buildRadialQuadtree(radialRoot);

    // Fit zoom to center
    radialTransform = computeFitTransform();
    d3.select(radialCanvas).call(radialZoom.transform, radialTransform);
    renderRadial();
    updateRadialBreadcrumb();
}

function buildSubtreeFromNode(node) {
    // Deep-copy the subtree as a d3.hierarchy
    const idKey = radialViewDef.hierarchy_options.id_key || 'id';
    const rankKey = radialViewDef.hierarchy_options.rank_key || 'rank';
    const tcOpts = radialViewDef.tree_chart_options || {};
    const countKey = tcOpts.count_key || radialViewDef.hierarchy_options.count_key;
    const labelKey = radialViewDef.hierarchy_options.label_key || 'name';
    const leafRank = tcOpts.leaf_rank;

    function copyNode(src) {
        const copy = d3.hierarchy(src.data);
        copy.id = src.id;
        // Copy collapsed state
        if (src._children && !src.children) {
            copy.children = null;
            copy._children = src._children.map(copyNode);
        } else if (src.children) {
            copy.children = src.children.map(copyNode);
            if (copy.children.length === 0) copy.children = null;
        } else {
            copy.children = null;
        }
        // Set parent references
        if (copy.children) {
            copy.children.forEach(c => { c.parent = copy; });
        }
        if (copy._children) {
            copy._children.forEach(c => { c.parent = copy; });
        }
        return copy;
    }

    const root = copyNode(node);
    root.parent = null;

    // Recompute counts
    if (countKey) {
        root.sum(d => d[countKey] || 0);
    } else {
        root.count();
    }

    // Sort
    root.sort((a, b) => {
        const aIsLeaf = leafRank && a.data[rankKey] === leafRank;
        const bIsLeaf = leafRank && b.data[rankKey] === leafRank;
        if (aIsLeaf !== bIsLeaf) return aIsLeaf ? 1 : -1;
        return (a.data[labelKey] || '').localeCompare(b.data[labelKey] || '');
    });

    return root;
}

function clearSubtreeRoot() {
    radialSubtreeNode = null;
    radialRoot = radialDepthHidden && radialPrunedRoot ? radialPrunedRoot : radialFullRoot;
    computeLayout(radialRoot, radialViewDef);
    assignRadialColors(radialRoot, radialViewDef);
    buildRadialQuadtree(radialRoot);
    radialTransform = computeFitTransform();
    d3.select(radialCanvas).call(radialZoom.transform, radialTransform);
    renderRadial();
    updateRadialBreadcrumb();
}

// --- Breadcrumb ---

function updateRadialBreadcrumb() {
    const bc = document.getElementById('tc-breadcrumb');
    if (!bc) return;

    if (!radialSubtreeNode) {
        bc.innerHTML = '';
        return;
    }

    const labelKey = radialViewDef.hierarchy_options.label_key || 'name';
    // Build path from the source tree's root to the subtree node
    const path = radialSubtreeNode.ancestors().reverse();
    const parts = [];

    // "All" link to go back to full tree
    parts.push('<span onclick="radialBcClick(null)">All</span>');

    path.forEach((node, i) => {
        if (isNodeHidden(node)) return;  // skip virtual root
        const label = node.data[labelKey] || node.id || 'Root';
        const isCurrent = node.id === radialSubtreeNode.id;
        const cls = isCurrent ? 'current' : '';
        parts.push(`<span class="${cls}" onclick="radialBcClick('${node.id}')">${label}</span>`);
    });

    bc.innerHTML = parts.join('<span class="bc-sep">/</span>');
}

function radialBcClick(nodeId) {
    if (!nodeId) {
        // Click "All" → back to full tree
        clearSubtreeRoot();
        return;
    }

    // Navigate to the clicked ancestor as subtree root
    navigateToSubtree(nodeId);
}

// --- Rendering ---

function resizeRadialCanvas() {
    const wrap = document.getElementById('tc-canvas-wrap');
    radialWidth = wrap.clientWidth;
    radialHeight = wrap.clientHeight;

    radialCanvas = document.getElementById('tc-canvas');
    radialCanvas.width = radialWidth * radialDpr;
    radialCanvas.height = radialHeight * radialDpr;
    radialCanvas.style.width = radialWidth + 'px';
    radialCanvas.style.height = radialHeight + 'px';

    radialCtx = radialCanvas.getContext('2d');
    radialCtx.setTransform(radialDpr, 0, 0, radialDpr, 0, 0);
}

function isNodeHidden(node) {
    // Always hide the virtual root inserted for multiple-root trees
    if (node.data[radialViewDef.hierarchy_options.id_key || 'id'] === '__virtual_root__') return true;
    return false;
}

function isLeafByRank(node) {
    const tcOpts = radialViewDef.tree_chart_options || {};
    const leafRank = tcOpts.leaf_rank;
    if (!leafRank) return !node.children || node.children.length === 0;
    const rankKey = radialViewDef.hierarchy_options.rank_key || 'rank';
    return node.data[rankKey] === leafRank;
}

function renderRadial() {
    if (!radialCtx || !radialRoot) return;

    const ctx = radialCtx;
    const t = radialTransform || d3.zoomIdentity;
    const cx = radialWidth / 2;
    const cy = radialHeight / 2;

    ctx.clearRect(0, 0, radialWidth, radialHeight);
    ctx.save();
    ctx.translate(t.x + cx * t.k, t.y + cy * t.k);
    ctx.scale(t.k, t.k);

    // Draw guide lines (circles for radial, vertical lines for rectangular)
    drawGuideLines(ctx);

    // Draw links
    drawLinks(ctx);

    // Draw nodes
    drawNodes(ctx, t.k);

    ctx.restore();

    // Update SVG labels (LOD)
    updateRadialLabels(t);
}

function drawGuideLines(ctx) {
    if (!radialRoot) return;

    ctx.strokeStyle = 'rgba(0, 0, 0, 0.06)';
    ctx.lineWidth = 0.5;
    ctx.setLineDash([4, 4]);

    if (treeLayoutMode === 'rectangular') {
        // Vertical dashed lines at each depth level
        const depths = new Set();
        radialRoot.each(d => { if (!isNodeHidden(d)) depths.add(d.cx); });

        for (const x of depths) {
            ctx.beginPath();
            ctx.moveTo(x, -cladoBoundsH / 2 - 20);
            ctx.lineTo(x, cladoBoundsH / 2 + 20);
            ctx.stroke();
        }
    } else {
        // Radial: concentric circles at each depth radius
        const depths = new Set();
        radialRoot.each(d => {
            if (!isNodeHidden(d)) depths.add(d.y);
        });

        for (const r of depths) {
            if (r === 0) continue;
            ctx.beginPath();
            ctx.arc(0, 0, r, 0, Math.PI * 2);
            ctx.stroke();
        }
    }

    ctx.setLineDash([]);
}

function drawLinks(ctx) {
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.lineWidth = 0.8;

    radialRoot.links().forEach(link => {
        if (isNodeHidden(link.source) || isNodeHidden(link.target)) return;

        ctx.beginPath();

        if (treeLayoutMode === 'rectangular') {
            // Elbow connector: vertical at parent x, then horizontal to child
            ctx.moveTo(link.source.cx, link.source.cy);
            ctx.lineTo(link.source.cx, link.target.cy);
            ctx.lineTo(link.target.cx, link.target.cy);
        } else {
            // Radial curved link
            ctx.moveTo(link.source.cx, link.source.cy);
            const midAngle = (link.source.x + link.target.x) / 2;
            const midR = (link.source.y + link.target.y) / 2;
            const midA = (midAngle - 90) * Math.PI / 180;
            const midX = midR * Math.cos(midA);
            const midY = midR * Math.sin(midA);
            ctx.quadraticCurveTo(midX, midY, link.target.cx, link.target.cy);
        }
        ctx.stroke();
    });
}

function drawNodes(ctx, k) {
    const searchIds = new Set(radialSearchMatches.map(d => d.id));

    radialRoot.each(node => {
        if (isNodeHidden(node)) return;

        const leaf = isLeafByRank(node);
        const isSearch = searchIds.has(node.id);

        // Node size: bigger for higher rank nodes
        let radius = leaf ? 2 : Math.max(3, 6 - node.depth);
        if (isSearch) radius = Math.max(radius, 5);

        // Draw node
        ctx.beginPath();
        ctx.arc(node.cx, node.cy, radius, 0, Math.PI * 2);
        ctx.fillStyle = isSearch ? '#ff6b35' : (node._color || '#6c757d');
        ctx.fill();

        if (isSearch) {
            ctx.strokeStyle = '#ff6b35';
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // Collapsed indicator: filled circle with border
        if (node._children) {
            ctx.beginPath();
            ctx.arc(node.cx, node.cy, radius + 3, 0, Math.PI * 2);
            ctx.strokeStyle = node._color || '#6c757d';
            ctx.lineWidth = 2;
            ctx.stroke();
            // Small "+" sign
            const s = radius + 1;
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(node.cx - s, node.cy);
            ctx.lineTo(node.cx + s, node.cy);
            ctx.moveTo(node.cx, node.cy - s);
            ctx.lineTo(node.cx, node.cy + s);
            ctx.stroke();
        }
        // Arc for internal nodes with value (count)
        else if (!leaf && node.value > 0 && k > 1) {
            const arcThickness = Math.min(node.value / (radialRoot.value || 1) * 8, 4);
            if (arcThickness > 0.3) {
                ctx.beginPath();
                ctx.arc(node.cx, node.cy, radius + 2, 0, Math.PI * 2);
                ctx.strokeStyle = node._color || '#6c757d';
                ctx.globalAlpha = 0.3;
                ctx.lineWidth = arcThickness;
                ctx.stroke();
                ctx.globalAlpha = 1.0;
            }
        }
    });
}

// --- SVG Labels (LOD) ---

function updateRadialLabels(t) {
    if (!radialLabelsSvg || !radialRoot) return;

    const k = t.k;
    const cx = radialWidth / 2;
    const cy = radialHeight / 2;
    const labelKey = radialViewDef.hierarchy_options.label_key || 'name';
    const rankKey = radialViewDef.hierarchy_options.rank_key || 'rank';

    // Determine which nodes get labels based on zoom level
    const labelsToShow = [];
    const maxLabels = 500;
    const tcOpts = radialViewDef.tree_chart_options || {};
    const leafRank = tcOpts.leaf_rank;

    // Viewport bounds in data coordinates
    const vpLeft = (-t.x - cx * t.k) / t.k;
    const vpTop = (-t.y - cy * t.k) / t.k;
    const vpRight = vpLeft + radialWidth / t.k;
    const vpBottom = vpTop + radialHeight / t.k;

    // Use rank (not d3 leaf status) to decide leaf vs non-leaf
    function isLeafRank(node) {
        return leafRank && node.data[rankKey] === leafRank;
    }

    radialRoot.each(node => {
        if (isNodeHidden(node)) return;

        let show = false;

        if (!isLeafRank(node)) {
            // Non-leaf ranks — always show
            show = true;
        } else {
            // Leaf rank — show based on zoom and viewport
            if (k >= 2) {
                show = node.cx >= vpLeft && node.cx <= vpRight &&
                       node.cy >= vpTop && node.cy <= vpBottom;
            }
        }

        if (show) labelsToShow.push(node);
    });

    // Limit labels
    const limited = labelsToShow.slice(0, maxLabels);

    // Font size by rank — scales at 50% of zoom rate
    const zoomScale = Math.min(0.5 + 0.5 * k, 4);
    function fontSize(d) {
        const rank = d.data[rankKey];
        let base;
        if (rank === leafRank) { base = 9; }
        else {
            const rr = tcOpts.rank_radius;
            if (rr && rr[rank] !== undefined) {
                base = rr[rank] <= 0.25 ? 12 : 10;
            } else {
                base = d.depth <= 1 ? 12 : 10;
            }
        }
        return (base * zoomScale) + 'px';
    }

    // Update SVG
    const sel = radialLabelsSvg.selectAll('text')
        .data(limited, d => d.id);

    sel.exit().remove();

    const isRect = treeLayoutMode === 'rectangular';

    // In rectangular mode, a node is "visually leaf" if it's leaf by rank OR has no children
    function isRectLeaf(d) {
        return isLeafRank(d) || (!d.children && !d._children);
    }

    const enter = sel.enter().append('text')
        .attr('font-size', fontSize)
        .attr('fill', '#212529')
        .attr('text-anchor', d => {
            if (isRect) {
                return isRectLeaf(d) ? 'start' : 'end';
            }
            const angle = d.x || 0;
            return (angle > 0 && angle < 180) ? 'start' : 'end';
        })
        .attr('dominant-baseline', 'central');

    const merged = enter.merge(sel);

    const labelOffset = 8 * zoomScale;
    merged
        .attr('transform', d => {
            const sx = t.x + (d.cx + cx) * t.k;
            const sy = t.y + (d.cy + cy) * t.k;
            if (isRect) {
                if (isRectLeaf(d)) {
                    // Leaf: label to the right of node
                    return `translate(${sx + labelOffset}, ${sy})`;
                }
                // Internal: label at top-left shoulder of node
                return `translate(${sx - labelOffset * 0.5}, ${sy - labelOffset})`;
            }
            // Radial: rotated labels
            const angle = d.x || 0;
            let rotation = angle > 180 ? angle - 270 : angle - 90;
            return `translate(${sx + labelOffset * (angle > 0 && angle < 180 ? 1 : -1)}, ${sy}) rotate(${rotation})`;
        })
        .attr('text-anchor', d => {
            if (isRect) {
                return isRectLeaf(d) ? 'start' : 'end';
            }
            const angle = d.x || 0;
            return (angle > 0 && angle < 180) ? 'start' : 'end';
        })
        .attr('font-size', fontSize)
        .attr('opacity', d => {
            if (!isLeafRank(d)) return 1;
            return Math.min(1, (k - 1.5) * 0.5);
        })
        .text(d => {
            const label = d.data[labelKey] || d.id || '';
            const maxLen = isLeafRank(d) ? 20 : 30;
            return label.length > maxLen ? label.substring(0, maxLen) + '...' : label;
        });
}

// --- Resize Handling ---

let radialResizeTimer = null;
window.addEventListener('resize', () => {
    if (!radialViewDef) return;
    clearTimeout(radialResizeTimer);
    radialResizeTimer = setTimeout(() => {
        const container = document.getElementById('view-tree-chart');
        if (container && container.style.display !== 'none') {
            resizeRadialCanvas();
            if (radialRoot) {
                computeLayout(radialRoot, radialViewDef);
                buildRadialQuadtree(radialRoot);
                renderRadial();
            }
        }
    }, 200);
});
