/**
 * SCODA Desktop — Tree Chart View (Radial + Rectangular)
 * D3-based tree visualization for hierarchy data.
 * Supports two layout modes: radial (concentric) and rectangular (cladogram).
 * Lazy-loads D3.js only when this view is activated.
 *
 * Refactored to TreeChartInstance class for multi-instance support (side-by-side).
 */

// D3 lazy load state
let d3Ready = null;

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

// Instance tracking
let _allInstances = [];
let _singletonTC = null;

// Global listeners (registered once)
let _globalListenersRegistered = false;
function _registerGlobalListeners() {
    if (_globalListenersRegistered) return;
    _globalListenersRegistered = true;
    document.addEventListener('click', () => {
        for (const inst of _allInstances) {
            inst.hideContextMenu();
        }
    });
    document.addEventListener('contextmenu', (e) => {
        const isInstanceCanvas = _allInstances.some(inst => inst.canvas === e.target);
        if (!isInstanceCanvas) {
            for (const inst of _allInstances) {
                inst.hideContextMenu();
            }
        }
    });
}

// Resize handler
let _resizeTimer = null;
window.addEventListener('resize', () => {
    clearTimeout(_resizeTimer);
    _resizeTimer = setTimeout(() => {
        for (const inst of _allInstances) {
            inst._onResize();
        }
    }, 200);
});


class TreeChartInstance {
    constructor(options = {}) {
        this.wrapEl = options.wrapEl;
        this.toolbarEl = options.toolbarEl || null;
        this.breadcrumbEl = options.breadcrumbEl || null;
        this.tooltipEl = options.tooltipEl || null;
        this.contextMenuEl = options.contextMenuEl || null;
        this.overrideParams = options.overrideParams || {};

        // State
        this.root = null;
        this.fullRoot = null;
        this.prunedRoot = null;
        this.subtreeNode = null;
        this.viewDef = null;
        this.viewKey = null;
        this.transform = null;
        this.quadtree = null;
        this.colorMap = {};
        this.focusNode = null;
        this.depthHidden = true;
        this.searchMatches = [];
        this.canvas = null;
        this.ctx = null;
        this.labelsSvg = null;
        this.zoom = null;
        this.dpr = window.devicePixelRatio || 1;
        this.width = 0;
        this.height = 0;
        this.outerRadius = 0;
        this.layoutMode = 'radial';
        this.cladoBoundsW = 0;
        this.cladoBoundsH = 0;
        this.contextTarget = null;
        this.hoverNodeId = null;       // ID of hovered node (for cross-instance highlight)
        this.onHoverSync = null;       // callback: (nodeId) => {} for cross-instance hover
        this.onDepthToggleSync = null; // callback: (depthHidden) => {} for cross-instance depth
        this.onCollapseSync = null;    // callback: (nodeId, collapsed) => {} for cross-instance collapse
        this.onSubtreeSync = null;     // callback: (nodeId|null) => {} for cross-instance view-as-root
        this._guideDepths = null;      // cached guide line depths
        this._zooming = false;         // true during active zoom gesture
        this.diffMode = false;         // true when rendering diff tree
        this.diffNodeMap = null;       // Map<nodeId, {cx, cy}> for ghost edges (old parent positions)
        this._cacheCanvas = null;      // offscreen canvas for zoom bitmap cache
        this._cacheCtx = null;
        this._cacheTransform = null;   // transform used when cache was rendered

        _allInstances.push(this);
        _registerGlobalListeners();
    }

    destroy() {
        const idx = _allInstances.indexOf(this);
        if (idx >= 0) _allInstances.splice(idx, 1);
        if (_singletonTC === this) _singletonTC = null;
        if (this.canvas) {
            d3.select(this.canvas).on('.zoom', null);
            d3.select(this.canvas).on('mousemove', null);
            d3.select(this.canvas).on('click', null);
            d3.select(this.canvas).on('contextmenu', null);
        }
    }

    // --- Main Entry ---

    async load(viewKey) {
        this.wrapEl.innerHTML = '<div class="loading">Loading D3.js...</div>';

        try {
            await ensureD3Loaded();
        } catch (e) {
            this.wrapEl.innerHTML = '<div class="text-danger">Failed to load D3.js. Check your internet connection.</div>';
            return;
        }

        // Create canvas + SVG inside wrap
        this.wrapEl.innerHTML = '<canvas></canvas><svg></svg>';

        const view = manifest.views[viewKey];
        if (!view) return;

        this.viewDef = view;
        this.viewKey = viewKey;
        this.depthHidden = true;
        this.searchMatches = [];
        this.focusNode = null;
        this.subtreeNode = null;

        const tcOpts = view.tree_chart_options || {};
        this.layoutMode = tcOpts.default_layout || 'radial';

        // Setup canvas
        this.canvas = this.wrapEl.querySelector('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.labelsSvg = d3.select(this.wrapEl.querySelector('svg'));
        this.dpr = window.devicePixelRatio || 1;

        this.resizeCanvas();

        // Build toolbar
        if (this.toolbarEl) this.buildToolbar(view);

        // Fetch data and build hierarchy
        try {
            await this.buildHierarchy(view);
        } catch (e) {
            this.wrapEl.innerHTML = `<div class="text-danger">Error loading data: ${e.message}</div>`;
            return;
        }

        // Start with pruned tree if available, otherwise full
        this.root = this.prunedRoot || this.fullRoot;
        if (!this.root) {
            this.wrapEl.innerHTML = '<div class="text-muted" style="padding:20px;text-align:center;">No hierarchy data found.</div>';
            return;
        }

        // Compute layout
        this.computeLayout(this.root, view);

        // Assign colors
        this.assignColors(this.root, view);

        // Build quadtree for hover
        this.buildQuadtree(this.root);

        // Setup zoom
        this.setupZoom();

        // Initial render — fit zoom if tree exceeds canvas
        this.transform = this.computeFitTransform();
        d3.select(this.canvas).call(this.zoom.transform, this.transform);
        this.render();
        if (this.breadcrumbEl) this.updateBreadcrumb();
    }

    // --- Data Loading ---

    async buildHierarchy(view) {
        const hOpts = view.hierarchy_options;
        const tcOpts = view.tree_chart_options || {};
        const rows = await fetchQuery(view.source_query, this.overrideParams);

        if (!rows || rows.length === 0) return null;

        // Determine edge source: diff_mode or normal edge_query
        const diffCfg = tcOpts.diff_mode || null;
        const edgeQuery = diffCfg ? diffCfg.edge_query : tcOpts.edge_query;
        const edgeParamsDef = diffCfg ? diffCfg.edge_params : tcOpts.edge_params;
        this.diffMode = !!diffCfg;

        if (edgeQuery) {
            // Resolve $variable references using effective controls (globalControls + overrides)
            const effectiveControls = { ...globalControls, ...this.overrideParams };
            const resolvedParams = {};
            for (const [k, v] of Object.entries(edgeParamsDef || {})) {
                resolvedParams[k] = (typeof v === 'string' && v.startsWith('$'))
                    ? (effectiveControls[v.slice(1)] ?? v) : v;
            }
            console.log(`[tree_chart] edge_query="${edgeQuery}" resolvedParams=`, JSON.stringify(resolvedParams), 'overrideParams=', JSON.stringify(this.overrideParams));
            const edges = await fetchQuery(edgeQuery, { ...this.overrideParams, ...resolvedParams });
            console.log(`[tree_chart] edge_query="${edgeQuery}" returned ${edges.length} edges`);
            const childKey = tcOpts.edge_child_key || 'child_id';
            const parentKey = tcOpts.edge_parent_key || 'parent_id';

            // For diff mode, build diff status map
            const diffStatusMap = diffCfg ? new Map() : null;
            if (diffCfg) {
                for (const e of edges) {
                    diffStatusMap.set(String(e[childKey]), {
                        diff_status: e.diff_status || 'same',
                        parent_id_a: e.parent_id_a,
                        parent_id_b: e.parent_id_b,
                    });
                }
            }

            // Use String keys to avoid number/string type mismatch between queries
            const parentMap = new Map(edges.map(e => [String(e[childKey]), e[parentKey]]));
            const edgeChildIds = new Set(edges.map(e => String(e[childKey])));
            rows.forEach(n => {
                const nid = String(n[hOpts.id_key]);
                const mapped = parentMap.get(nid);
                n[hOpts.parent_key] = mapped !== undefined ? mapped : null;
                // Attach diff info to row data
                if (diffStatusMap) {
                    const info = diffStatusMap.get(nid);
                    n._diff_status = info ? info.diff_status : 'same';
                    n._parent_id_a = info ? info.parent_id_a : null;
                    n._parent_id_b = info ? info.parent_id_b : null;
                    // Re-parent moved nodes to their compare profile parent
                    if (info && info.diff_status === 'moved' && info.parent_id_b != null) {
                        n[hOpts.parent_key] = info.parent_id_b;
                    }
                }
            });

            // Remove orphan nodes (not part of the classification tree)
            const edgeParentIds = new Set(edges.map(e => String(e[parentKey])));
            const before = rows.length;
            const filtered = rows.filter(n => {
                const id = String(n[hOpts.id_key]);
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
            tree.sort((a, b) => {
                const aIsLeaf = leafRank && a.data[rankKey] === leafRank;
                const bIsLeaf = leafRank && b.data[rankKey] === leafRank;
                if (aIsLeaf !== bIsLeaf) return aIsLeaf ? 1 : -1;
                return (a.data[labelKey] || '').localeCompare(b.data[labelKey] || '');
            });
            return tree;
        }

        // Full tree (all nodes)
        this.fullRoot = buildTree(rows);

        // Pruned tree (leaf rank removed) — for depth toggle
        if (leafRank) {
            const prunedRows = rows.filter(r => r[rankKey] !== leafRank);
            if (prunedRows.length > 0) {
                this.prunedRoot = buildTree(prunedRows);
            }
        }

        return this.fullRoot;
    }

    // --- Layout Dispatcher ---

    computeLayout(root, view) {
        this.invalidateGuideCache();
        if (this.layoutMode === 'rectangular') {
            this.computeCladogramLayout(root, view);
        } else {
            this.computeRadialLayout(root, view);
        }
    }

    // --- Radial Layout ---

    computeRadialLayout(root, view) {
        const tcOpts = view.tree_chart_options || {};
        const rankKey = view.hierarchy_options.rank_key || 'rank';
        this.outerRadius = Math.min(this.width, this.height) * 0.42;

        const LEAF_GAP_DEG = 2;
        const SUBTREE_GAP_DEG = 1;
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

        const totalAngle = nextAngle || 1;
        root.each(node => {
            node.x = (node._la / totalAngle) * 360;
            node.y = node.depth * (this.outerRadius / (root.height || 1));
        });

        // Dynamic radius: ensure minimum arc spacing between adjacent leaves
        const MIN_SPACING = 20;
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
                const minArc = this.outerRadius * minDeltaRad;
                if (minArc < MIN_SPACING) {
                    const scaleFactor = MIN_SPACING / minArc;
                    this.outerRadius *= scaleFactor;
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
                    node.y = rankRadius[rank] * this.outerRadius;
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

    computeCladogramLayout(root, view) {
        const tcOpts = view.tree_chart_options || {};
        const rankKey = view.hierarchy_options.rank_key || 'rank';

        const LEAF_GAP = 6;
        const SUBTREE_GAP = 8;
        let nextY = 0;

        function layoutSubtree(node) {
            if (!node.children || node.children.length === 0) {
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
            const first = node.children[0];
            const last = node.children[node.children.length - 1];
            node._ly = (first._ly + last._ly) / 2;
        }

        layoutSubtree(root);

        const treeH = Math.max(nextY, LEAF_GAP);
        const maxDepth = root.height || 1;
        const depthSpacing = 120;
        const treeW = maxDepth * depthSpacing;

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
            const rankSum = {};
            const rankCount = {};
            root.each(node => {
                if (this.isNodeHidden(node)) return;
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

        this.cladoBoundsW = treeW;
        this.cladoBoundsH = treeH;

        // d3 tree: node.x = vertical spread [0, treeH], node.y = depth [0, treeW]
        // Map to centered cartesian (left-to-right tree)
        root.each(node => {
            node.cx = node.y - treeW / 2;
            node.cy = node.x - treeH / 2;
        });
    }

    // --- Fit Transform ---

    computeFitTransform() {
        if (this.layoutMode === 'rectangular') {
            const padding = 120;
            const scaleX = this.width / (this.cladoBoundsW + padding);
            const scaleY = this.height / (this.cladoBoundsH + padding);
            const fitScale = Math.min(scaleX, scaleY);
            if (fitScale < 1) return d3.zoomIdentity.scale(fitScale);
            return d3.zoomIdentity;
        }
        // Radial mode
        const padding = 40;
        const fitScale = Math.min(this.width, this.height) / (2 * this.outerRadius + padding);
        if (fitScale < 1) {
            return d3.zoomIdentity.scale(fitScale);
        }
        return d3.zoomIdentity;
    }

    // --- Colors ---

    assignColors(root, view) {
        const tcOpts = view.tree_chart_options || {};

        // Diff mode: use diff status colors
        if (this.diffMode && tcOpts.diff_mode) {
            const colors = tcOpts.diff_mode.colors || {};
            root.each(node => {
                const status = node.data._diff_status || 'same';
                node._color = colors[status] || colors.same || '#adb5bd';
            });
            return;
        }

        const colorKey = tcOpts.color_key;
        this.colorMap = {};

        const topChildren = root.children || [];
        const palette = d3.schemeTableau10;

        topChildren.forEach((child, i) => {
            const color = palette[i % palette.length];
            this.colorMap[child.id] = color;
            child.each(d => {
                d._color = color;
            });
        });

        root._color = '#6c757d';

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

    buildQuadtree(root) {
        const nodes = [];
        root.each(d => nodes.push(d));
        this.quadtree = d3.quadtree()
            .x(d => d.cx)
            .y(d => d.cy)
            .addAll(nodes);
    }

    // --- Toolbar ---

    buildToolbar(view) {
        const toolbar = this.toolbarEl;
        if (!toolbar) return;

        const tcOpts = view.tree_chart_options || {};
        let html = '';

        // Search
        html += '<input type="text" class="tc-search" placeholder="Search nodes..." autocomplete="off">';

        // Layout toggle
        const radialActive = this.layoutMode === 'radial' ? ' active' : '';
        const rectActive = this.layoutMode === 'rectangular' ? ' active' : '';
        html += `<button class="tc-layout-btn tc-layout-radial${radialActive}" title="Radial layout"><i class="bi bi-bullseye"></i></button>`;
        html += `<button class="tc-layout-btn tc-layout-rect${rectActive}" title="Rectangular layout"><i class="bi bi-diagram-3"></i></button>`;

        // Depth toggle (starts active = pruned)
        if (tcOpts.depth_toggle && tcOpts.leaf_rank) {
            html += `<button class="tc-depth-btn active" title="Toggle leaf nodes">
                        <i class="bi bi-layers"></i> ${tcOpts.leaf_rank}
                     </button>`;
        }

        // Reset zoom
        html += '<button class="tc-reset-btn" title="Reset zoom"><i class="bi bi-arrows-fullscreen"></i></button>';

        toolbar.innerHTML = html;

        // Event: search
        const searchInput = toolbar.querySelector('.tc-search');
        if (searchInput) {
            let timer;
            searchInput.addEventListener('input', () => {
                clearTimeout(timer);
                timer = setTimeout(() => this.search(searchInput.value.trim()), 200);
            });
        }

        // Event: layout toggle
        const radialBtn = toolbar.querySelector('.tc-layout-radial');
        const rectBtn = toolbar.querySelector('.tc-layout-rect');
        if (radialBtn && rectBtn) {
            radialBtn.addEventListener('click', () => this.switchLayout('radial'));
            rectBtn.addEventListener('click', () => this.switchLayout('rectangular'));
        }

        // Event: depth toggle
        const depthBtn = toolbar.querySelector('.tc-depth-btn');
        if (depthBtn) {
            depthBtn.addEventListener('click', () => {
                this.depthHidden = !this.depthHidden;
                depthBtn.classList.toggle('active', this.depthHidden);
                if (this.subtreeNode) {
                    this.navigateToSubtree(this.subtreeNode.id);
                } else {
                    this.root = this.depthHidden && this.prunedRoot ? this.prunedRoot : this.fullRoot;
                    this.computeLayout(this.root, this.viewDef);
                    this.assignColors(this.root, this.viewDef);
                    this.buildQuadtree(this.root);
                    this.transform = this.computeFitTransform();
                    d3.select(this.canvas).call(this.zoom.transform, this.transform);
                    this.render();
                }
                if (this.onDepthToggleSync) this.onDepthToggleSync(this.depthHidden);
            });
        }

        // Event: reset
        const resetBtn = toolbar.querySelector('.tc-reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.focusNode = null;
                if (this.subtreeNode) {
                    this.clearSubtreeRoot();
                } else {
                    d3.select(this.canvas)
                        .transition().duration(500)
                        .call(this.zoom.transform, this.computeFitTransform());
                }
            });
        }
    }

    switchLayout(mode) {
        if (mode === this.layoutMode) return;
        this.layoutMode = mode;

        // Update toolbar button active states
        if (this.toolbarEl) {
            const radialBtn = this.toolbarEl.querySelector('.tc-layout-radial');
            const rectBtn = this.toolbarEl.querySelector('.tc-layout-rect');
            if (radialBtn) radialBtn.classList.toggle('active', mode === 'radial');
            if (rectBtn) rectBtn.classList.toggle('active', mode === 'rectangular');
        }

        if (this.root) {
            this.computeLayout(this.root, this.viewDef);
            this.buildQuadtree(this.root);
            this.transform = this.computeFitTransform();
            d3.select(this.canvas).call(this.zoom.transform, this.transform);
            this.render();
        }
    }

    // --- Search ---

    search(term) {
        this.searchMatches = [];
        if (!term || !this.root) {
            this.render();
            return;
        }

        const lower = term.toLowerCase();
        const labelKey = this.viewDef.hierarchy_options.label_key || 'name';

        this.root.each(d => {
            const label = (d.data[labelKey] || '').toLowerCase();
            if (label.includes(lower)) {
                this.searchMatches.push(d);
            }
        });

        if (this.searchMatches.length > 0) {
            const target = this.searchMatches[0];
            this.zoomToNode(target, 4);
        }

        this.render();
    }

    // --- Zoom ---

    setupZoom() {
        this.zoom = d3.zoom()
            .scaleExtent([0.3, 30])
            .on('start', () => {
                this._zooming = true;
                this._snapshotCache();
            })
            .on('zoom', (event) => {
                this.transform = event.transform;
                this.render();
            })
            .on('end', () => {
                this._zooming = false;
                this._cacheTransform = null; // invalidate cache → next render is full
                this.render();
                this.updateLabels(this.transform || d3.zoomIdentity);
            });

        d3.select(this.canvas)
            .call(this.zoom)
            .on('dblclick.zoom', null)
            .on('mousemove', (event) => this.onMouseMove(event))
            .on('mouseleave', () => {
                if (this.hoverNodeId !== null) {
                    this.hoverNodeId = null;
                    if (this.tooltipEl) this.tooltipEl.style.display = 'none';
                    this.render();
                    if (this.onHoverSync) this.onHoverSync(null);
                }
            })
            .on('click', (event) => this.onClick(event))
            .on('contextmenu', (event) => this.onContextMenu(event));
    }

    zoomToNode(node, scale) {
        if (!node || !this.zoom) return;
        scale = scale || 4;
        const cx = this.width / 2;
        const cy = this.height / 2;
        const transform = d3.zoomIdentity
            .translate(cx, cy)
            .scale(scale)
            .translate(-node.cx, -node.cy);

        d3.select(this.canvas)
            .transition().duration(600)
            .call(this.zoom.transform, transform);
    }

    // --- Interaction: Mouse ---

    onMouseMove(event) {
        if (!this.quadtree || !this.transform) return;

        const [mx, my] = d3.pointer(event, this.canvas);
        const cx = this.width / 2;
        const cy = this.height / 2;

        const dx = (mx - this.transform.x - cx * this.transform.k) / this.transform.k + cx;
        const dy = (my - this.transform.y - cy * this.transform.k) / this.transform.k + cy;
        const dataX = dx - cx;
        const dataY = dy - cy;

        const searchRadius = 15 / this.transform.k;
        const nearest = this.quadtree.find(dataX, dataY, searchRadius);

        const newHoverId = (nearest && !this.isNodeHidden(nearest)) ? nearest.id : null;
        const hoverChanged = newHoverId !== this.hoverNodeId;
        this.hoverNodeId = newHoverId;

        const tooltip = this.tooltipEl;
        if (nearest && !this.isNodeHidden(nearest) && tooltip) {
            const labelKey = this.viewDef.hierarchy_options.label_key || 'name';
            const rankKey = this.viewDef.hierarchy_options.rank_key || 'rank';
            const tcOpts = this.viewDef.tree_chart_options || {};
            const countKey = tcOpts.count_key || this.viewDef.hierarchy_options.count_key;

            let html = `<div class="tc-tt-name">${nearest.data[labelKey] || nearest.id}</div>`;
            if (nearest.data[rankKey]) {
                html += `<div class="tc-tt-rank">${nearest.data[rankKey]}</div>`;
            }
            if (countKey && nearest.value !== undefined) {
                html += `<div class="tc-tt-count">${countKey}: ${nearest.value}</div>`;
            }
            // Diff mode: show diff status + moved parent info
            if (this.diffMode && nearest.data._diff_status && nearest.data._diff_status !== 'same') {
                const status = nearest.data._diff_status;
                const statusLabel = { moved: 'Moved', added: 'Added', removed: 'Removed' }[status] || status;
                html += `<div class="tc-tt-diff" style="color:${(tcOpts.diff_mode?.colors?.[status]) || '#666'};font-weight:bold;">${statusLabel}</div>`;
                if (status === 'moved' && nearest.data._parent_id_b) {
                    const baseParentName = nearest.data._parent_id_a ? (this._getNodeLabel(String(nearest.data._parent_id_a), labelKey) || '?') : '?';
                    const compareParentName = this._getNodeLabel(String(nearest.data._parent_id_b), labelKey) || '?';
                    html += `<div class="tc-tt-diff-detail" style="font-size:0.85em;color:#888;">${baseParentName} → ${compareParentName}</div>`;
                }
            }

            tooltip.innerHTML = html;
            tooltip.style.display = '';
            tooltip.style.left = (mx + 12) + 'px';
            tooltip.style.top = (my - 10) + 'px';

            // Keep tooltip inside viewport
            const rect = tooltip.getBoundingClientRect();
            const wrapRect = this.wrapEl.getBoundingClientRect();
            if (rect.right > wrapRect.right) {
                tooltip.style.left = (mx - rect.width - 8) + 'px';
            }
            if (rect.bottom > wrapRect.bottom) {
                tooltip.style.top = (my - rect.height - 8) + 'px';
            }
        } else if (tooltip) {
            tooltip.style.display = 'none';
        }

        if (hoverChanged) {
            if (!this._zooming) this.render();
            if (this.onHoverSync) this.onHoverSync(this.hoverNodeId);
        }
    }

    setHoverNode(nodeId) {
        if (nodeId === this.hoverNodeId) return;
        this.hoverNodeId = nodeId;
        if (!this._zooming) this.render();
        this._showTooltipForNode(nodeId);
    }

    _showTooltipForNode(nodeId) {
        const tooltip = this.tooltipEl;
        if (!tooltip) return;

        if (!nodeId) {
            tooltip.style.display = 'none';
            return;
        }

        // Find the node in the tree
        let node = null;
        if (this.root) this.root.each(d => { if (d.id === nodeId) node = d; });
        if (!node) {
            tooltip.style.display = 'none';
            return;
        }

        const t = this.transform || d3.zoomIdentity;
        const cx = this.width / 2;
        const cy = this.height / 2;

        // Convert node data coords to screen coords
        const sx = t.x + (node.cx + cx) * t.k;
        const sy = t.y + (node.cy + cy) * t.k;

        const labelKey = this.viewDef.hierarchy_options.label_key || 'name';
        const rankKey = this.viewDef.hierarchy_options.rank_key || 'rank';
        const tcOpts = this.viewDef.tree_chart_options || {};
        const countKey = tcOpts.count_key || this.viewDef.hierarchy_options.count_key;

        let html = `<div class="tc-tt-name">${node.data[labelKey] || node.id}</div>`;
        if (node.data[rankKey]) {
            html += `<div class="tc-tt-rank">${node.data[rankKey]}</div>`;
        }
        if (countKey && node.value !== undefined) {
            html += `<div class="tc-tt-count">${countKey}: ${node.value}</div>`;
        }
        if (this.diffMode && node.data._diff_status && node.data._diff_status !== 'same') {
            const status = node.data._diff_status;
            const statusLabel = { moved: 'Moved', added: 'Added', removed: 'Removed' }[status] || status;
            html += `<div style="color:${(tcOpts.diff_mode?.colors?.[status]) || '#666'};font-weight:bold;">${statusLabel}</div>`;
            if (status === 'moved' && node.data._parent_id_b) {
                const baseParentName = node.data._parent_id_a ? (this._getNodeLabel(String(node.data._parent_id_a), labelKey) || '?') : '?';
                const compareParentName = this._getNodeLabel(String(node.data._parent_id_b), labelKey) || '?';
                html += `<div style="font-size:0.85em;color:#888;">${baseParentName} → ${compareParentName}</div>`;
            }
        }

        tooltip.innerHTML = html;
        tooltip.style.display = '';
        tooltip.style.left = (sx + 12) + 'px';
        tooltip.style.top = (sy - 10) + 'px';
    }

    setDepthHidden(hidden) {
        if (hidden === this.depthHidden) return;
        this.depthHidden = hidden;
        // Update toolbar button state if present
        if (this.toolbarEl) {
            const depthBtn = this.toolbarEl.querySelector('.tc-depth-btn');
            if (depthBtn) depthBtn.classList.toggle('active', this.depthHidden);
        }
        if (this.subtreeNode) {
            this.navigateToSubtree(this.subtreeNode.id);
        } else {
            this.root = this.depthHidden && this.prunedRoot ? this.prunedRoot : this.fullRoot;
            this.computeLayout(this.root, this.viewDef);
            this.assignColors(this.root, this.viewDef);
            this.buildQuadtree(this.root);
            this.transform = this.computeFitTransform();
            d3.select(this.canvas).call(this.zoom.transform, this.transform);
            this.render();
        }
    }

    onClick(event) {
        if (!this.quadtree || !this.transform) return;

        const [mx, my] = d3.pointer(event, this.canvas);
        const cx = this.width / 2;
        const cy = this.height / 2;

        const dx = (mx - this.transform.x - cx * this.transform.k) / this.transform.k + cx;
        const dy = (my - this.transform.y - cy * this.transform.k) / this.transform.k + cy;
        const dataX = dx - cx;
        const dataY = dy - cy;

        const searchRadius = 15 / this.transform.k;
        const nearest = this.quadtree.find(dataX, dataY, searchRadius);

        if (!nearest || this.isNodeHidden(nearest)) return;

        const tcOpts = this.viewDef.tree_chart_options || {};
        const isLeaf = this.isLeafByRank(nearest);

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
        this.toggleNode(nearest);
    }

    toggleNode(node, _fromSync) {
        if (node._children) {
            node.children = node._children;
            node._children = null;
        } else if (node.children) {
            node._children = node.children;
            node.children = null;
        } else {
            return;
        }

        const collapsed = !!node._children;

        const tcOpts = this.viewDef.tree_chart_options || {};
        const countKey = tcOpts.count_key || this.viewDef.hierarchy_options.count_key;
        if (countKey) {
            this.root.sum(d => d[countKey] || 0);
        } else {
            this.root.count();
        }

        this.computeLayout(this.root, this.viewDef);
        this.assignColors(this.root, this.viewDef);
        this.buildQuadtree(this.root);
        this.render();

        if (!_fromSync && this.onCollapseSync) {
            this.onCollapseSync(node.id, collapsed);
        }
    }

    setNodeCollapsed(nodeId, collapsed) {
        const target = this._findNodeById(nodeId);
        if (!target) return;
        const isCollapsed = !!target._children;
        if (isCollapsed === collapsed) return;
        this.toggleNode(target, true);
    }

    _getNodeLabel(nodeId, labelKey) {
        const node = this._findNodeById(nodeId);
        return node ? (node.data[labelKey] || node.id) : null;
    }

    _findNodeById(nodeId) {
        let found = null;
        this.root.each(node => {
            if (node.id === nodeId) found = node;
        });
        // Also search collapsed subtrees
        if (!found) {
            const search = (node) => {
                if (node.id === nodeId) return node;
                if (node._children) {
                    for (const c of node._children) {
                        const r = search(c);
                        if (r) return r;
                    }
                }
                return null;
            };
            found = search(this.root);
        }
        return found;
    }

    // --- Context Menu ---

    onContextMenu(event) {
        event.preventDefault();
        if (!this.quadtree || !this.transform) return;

        const [mx, my] = d3.pointer(event, this.canvas);
        const cx = this.width / 2;
        const cy = this.height / 2;

        const dx = (mx - this.transform.x - cx * this.transform.k) / this.transform.k + cx;
        const dy = (my - this.transform.y - cy * this.transform.k) / this.transform.k + cy;
        const dataX = dx - cx;
        const dataY = dy - cy;

        const searchRadius = 15 / this.transform.k;
        const nearest = this.quadtree.find(dataX, dataY, searchRadius);

        if (!nearest || this.isNodeHidden(nearest)) {
            this.hideContextMenu();
            return;
        }

        this.contextTarget = nearest;
        this.showContextMenu(event, nearest);
    }

    showContextMenu(event, node) {
        const menu = this.contextMenuEl;
        if (!menu) return;

        // Hide tooltip
        if (this.tooltipEl) this.tooltipEl.style.display = 'none';

        const labelKey = this.viewDef.hierarchy_options.label_key || 'name';
        const rankKey = this.viewDef.hierarchy_options.rank_key || 'rank';
        const label = node.data[labelKey] || node.id;
        const rank = node.data[rankKey] || '';
        const isLeaf = this.isLeafByRank(node);
        const hasChildren = node.children || node._children;

        menu.innerHTML = '';

        // Header
        const header = document.createElement('div');
        header.style.cssText = 'padding:6px 14px;font-weight:600;font-size:0.8rem;color:#6c757d;border-bottom:1px solid #eee;';
        header.textContent = (rank ? rank + ': ' : '') + label;
        menu.appendChild(header);

        const addItem = (icon, text, handler) => {
            const item = document.createElement('div');
            item.className = 'tc-cm-item';
            item.innerHTML = `<i class="bi ${icon}"></i> ${text}`;
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this.hideContextMenu();
                handler();
            });
            menu.appendChild(item);
        };

        // "View as root" — only for internal nodes
        if (!isLeaf && hasChildren) {
            addItem('bi-diagram-3', 'View as root', () => this.setSubtreeRoot(node));
        }

        // "Expand / Collapse" — for internal nodes
        if (hasChildren) {
            if (node._children) {
                addItem('bi-chevron-expand', 'Expand', () => this.toggleNode(node));
            } else if (node.children) {
                addItem('bi-chevron-contract', 'Collapse', () => this.toggleNode(node));
            }
        }

        // "Zoom to" — always available
        addItem('bi-search', 'Zoom to', () => this.zoomToNode(node, 4));

        // "Detail" — for leaf nodes with detail_view configured
        const tcOpts = this.viewDef.tree_chart_options || {};
        if (isLeaf && tcOpts.on_node_click) {
            addItem('bi-info-circle', 'Detail', () => {
                const idKey = tcOpts.on_node_click.id_key || tcOpts.on_node_click.id_field;
                const detailView = tcOpts.on_node_click.detail_view;
                if (detailView && idKey && node.data[idKey] && typeof openDetailModal === 'function') {
                    openDetailModal(detailView, node.data[idKey]);
                }
            });
        }

        menu.style.display = 'block';

        // Position near the mouse, inside the canvas wrap
        const wrapRect = this.wrapEl.getBoundingClientRect();
        let left = event.clientX - wrapRect.left;
        let top = event.clientY - wrapRect.top;

        menu.style.left = left + 'px';
        menu.style.top = top + 'px';

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

    hideContextMenu() {
        if (this.contextMenuEl) this.contextMenuEl.style.display = 'none';
        this.contextTarget = null;
    }

    // --- Subtree Navigation ---

    setSubtreeRoot(node) {
        if (!node) return;

        if (this.subtreeNode && this.subtreeNode.id === node.id) {
            if (this.subtreeNode.parent && !this.isNodeHidden(this.subtreeNode.parent)) {
                this.navigateToSubtree(this.subtreeNode.parent.id);
            } else {
                this.clearSubtreeRoot();
            }
            return;
        }

        this.navigateToSubtree(node.id);
    }

    navigateToSubtree(nodeId, _fromSync) {
        const sourceTree = this.depthHidden && this.prunedRoot ? this.prunedRoot : this.fullRoot;

        let targetNode = null;
        sourceTree.each(d => { if (d.id === nodeId) targetNode = d; });
        if (!targetNode || this.isLeafByRank(targetNode)) return;

        this.subtreeNode = targetNode;

        const subtreeRoot = this.buildSubtreeFromNode(targetNode);
        if (!subtreeRoot) return;

        this.root = subtreeRoot;
        this.computeLayout(this.root, this.viewDef);
        this.assignColors(this.root, this.viewDef);
        this.buildQuadtree(this.root);

        this.transform = this.computeFitTransform();
        d3.select(this.canvas).call(this.zoom.transform, this.transform);
        this.render();
        if (this.breadcrumbEl) this.updateBreadcrumb();

        if (!_fromSync && this.onSubtreeSync) this.onSubtreeSync(nodeId);
    }

    buildSubtreeFromNode(node) {
        const idKey = this.viewDef.hierarchy_options.id_key || 'id';
        const rankKey = this.viewDef.hierarchy_options.rank_key || 'rank';
        const tcOpts = this.viewDef.tree_chart_options || {};
        const countKey = tcOpts.count_key || this.viewDef.hierarchy_options.count_key;
        const labelKey = this.viewDef.hierarchy_options.label_key || 'name';
        const leafRank = tcOpts.leaf_rank;

        function copyNode(src) {
            const copy = d3.hierarchy(src.data);
            copy.id = src.id;
            if (src._children && !src.children) {
                copy.children = null;
                copy._children = src._children.map(copyNode);
            } else if (src.children) {
                copy.children = src.children.map(copyNode);
                if (copy.children.length === 0) copy.children = null;
            } else {
                copy.children = null;
            }
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

        if (countKey) {
            root.sum(d => d[countKey] || 0);
        } else {
            root.count();
        }

        root.sort((a, b) => {
            const aIsLeaf = leafRank && a.data[rankKey] === leafRank;
            const bIsLeaf = leafRank && b.data[rankKey] === leafRank;
            if (aIsLeaf !== bIsLeaf) return aIsLeaf ? 1 : -1;
            return (a.data[labelKey] || '').localeCompare(b.data[labelKey] || '');
        });

        return root;
    }

    clearSubtreeRoot(_fromSync) {
        this.subtreeNode = null;
        this.root = this.depthHidden && this.prunedRoot ? this.prunedRoot : this.fullRoot;
        this.computeLayout(this.root, this.viewDef);
        this.assignColors(this.root, this.viewDef);
        this.buildQuadtree(this.root);
        this.transform = this.computeFitTransform();
        d3.select(this.canvas).call(this.zoom.transform, this.transform);
        this.render();
        if (this.breadcrumbEl) this.updateBreadcrumb();

        if (!_fromSync && this.onSubtreeSync) this.onSubtreeSync(null);
    }

    // --- Breadcrumb ---

    updateBreadcrumb() {
        const bc = this.breadcrumbEl;
        if (!bc) return;

        if (!this.subtreeNode) {
            bc.innerHTML = '';
            return;
        }

        const labelKey = this.viewDef.hierarchy_options.label_key || 'name';
        const path = this.subtreeNode.ancestors().reverse();

        bc.innerHTML = '';

        // "All" link
        const allSpan = document.createElement('span');
        allSpan.textContent = 'All';
        allSpan.addEventListener('click', () => this.clearSubtreeRoot());
        bc.appendChild(allSpan);

        path.forEach(node => {
            if (this.isNodeHidden(node)) return;

            const sep = document.createElement('span');
            sep.className = 'bc-sep';
            sep.textContent = '/';
            bc.appendChild(sep);

            const span = document.createElement('span');
            const label = node.data[labelKey] || node.id || 'Root';
            span.textContent = label;
            if (node.id === this.subtreeNode.id) span.className = 'current';
            span.addEventListener('click', () => this.navigateToSubtree(node.id));
            bc.appendChild(span);
        });
    }

    // --- Rendering ---

    resizeCanvas() {
        this.width = this.wrapEl.clientWidth;
        this.height = this.wrapEl.clientHeight;

        this.canvas.width = this.width * this.dpr;
        this.canvas.height = this.height * this.dpr;
        this.canvas.style.width = this.width + 'px';
        this.canvas.style.height = this.height + 'px';

        this.ctx = this.canvas.getContext('2d');
        this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    }

    isNodeHidden(node) {
        if (node.data[this.viewDef.hierarchy_options.id_key || 'id'] === '__virtual_root__') return true;
        return false;
    }

    isLeafByRank(node) {
        const tcOpts = this.viewDef.tree_chart_options || {};
        const leafRank = tcOpts.leaf_rank;
        if (!leafRank) return !node.children || node.children.length === 0;
        const rankKey = this.viewDef.hierarchy_options.rank_key || 'rank';
        return node.data[rankKey] === leafRank;
    }

    _snapshotCache() {
        if (!this.canvas) return;
        if (!this._cacheCanvas) {
            this._cacheCanvas = document.createElement('canvas');
        }
        const cw = this.canvas.width;
        const ch = this.canvas.height;
        if (this._cacheCanvas.width !== cw || this._cacheCanvas.height !== ch) {
            this._cacheCanvas.width = cw;
            this._cacheCanvas.height = ch;
        }
        const cctx = this._cacheCanvas.getContext('2d');
        cctx.clearRect(0, 0, cw, ch);
        cctx.drawImage(this.canvas, 0, 0);
        const t = this.transform || d3.zoomIdentity;
        this._cacheTransform = { x: t.x, y: t.y, k: t.k };
    }

    render() {
        if (!this.ctx || !this.root) return;

        const ctx = this.ctx;
        const t = this.transform || d3.zoomIdentity;

        // During scale change (zoom in/out): blit cached bitmap (skip full redraw)
        // Pan (translate only) is fast enough — render fully for crisp labels
        if (this._zooming && this._cacheTransform && t.k !== this._cacheTransform.k) {
            const ct = this._cacheTransform;
            const dpr = this.dpr;
            const ds = t.k / ct.k;

            ctx.save();
            ctx.setTransform(1, 0, 0, 1, 0, 0); // raw pixels
            ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            ctx.setTransform(ds, 0, 0, ds,
                (t.x - ct.x * ds) * dpr,
                (t.y - ct.y * ds) * dpr);
            ctx.drawImage(this._cacheCanvas, 0, 0);
            ctx.restore();
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

            // Hide labels during scale zoom — update only on zoom end
            this.labelsSvg.style('visibility', 'hidden');
            return;
        }

        const cx = this.width / 2;
        const cy = this.height / 2;

        ctx.clearRect(0, 0, this.width, this.height);
        ctx.save();
        ctx.translate(t.x + cx * t.k, t.y + cy * t.k);
        ctx.scale(t.k, t.k);

        this.drawGuideLines(ctx);
        this.drawLinks(ctx);
        this.drawNodes(ctx, t.k);

        ctx.restore();

        if (this.diffMode) this.drawDiffLegend(ctx);
        this.updateLabels(t);
    }

    drawDiffLegend(ctx) {
        const tcOpts = this.viewDef.tree_chart_options || {};
        const colors = tcOpts.diff_mode?.colors;
        if (!colors) return;

        // Count nodes per diff status
        const counts = { same: 0, moved: 0, added: 0, removed: 0 };
        this.root.each(node => {
            if (this.isNodeHidden(node)) return;
            const s = node.data._diff_status || 'same';
            if (counts[s] !== undefined) counts[s]++;
        });

        const items = [
            { label: `Same (${counts.same})`, color: colors.same, type: 'dot' },
            { label: `Moved (${counts.moved})`, color: colors.moved, type: 'dot' },
            { label: `Added (${counts.added})`, color: colors.added, type: 'dot' },
            { label: `Removed (${counts.removed})`, color: colors.removed, type: 'dot' },
        ];
        if (tcOpts.diff_mode.show_ghost_edges && counts.moved > 0) {
            items.push({ label: 'Original position', color: 'rgba(220, 53, 69, 0.5)', type: 'dash' });
        }

        const x = 12, y = 12;
        const lineH = 18, padX = 12, padY = 8;
        const boxW = 170, boxH = padY * 2 + items.length * lineH;

        ctx.save();
        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.strokeStyle = '#dee2e6';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(x, y, boxW, boxH, 4);
        ctx.fill();
        ctx.stroke();

        ctx.font = '11px sans-serif';
        items.forEach((item, i) => {
            const iy = y + padY + i * lineH + 12;
            if (item.type === 'dot') {
                ctx.fillStyle = item.color;
                ctx.beginPath();
                ctx.arc(x + padX, iy - 4, 5, 0, Math.PI * 2);
                ctx.fill();
            } else {
                ctx.setLineDash([4, 4]);
                ctx.strokeStyle = item.color;
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.moveTo(x + padX - 5, iy - 4);
                ctx.lineTo(x + padX + 5, iy - 4);
                ctx.stroke();
                ctx.setLineDash([]);
            }
            ctx.fillStyle = '#333';
            ctx.fillText(item.label, x + padX + 10, iy);
        });

        ctx.restore();
    }

    invalidateGuideCache() {
        this._guideDepths = null;
    }

    drawGuideLines(ctx) {
        if (!this.root) return;

        // Cache guide depths — only recompute when layout changes
        if (!this._guideDepths) {
            if (this.layoutMode === 'rectangular') {
                const s = new Set();
                this.root.each(d => { if (!this.isNodeHidden(d)) s.add(d.cx); });
                this._guideDepths = [...s];
            } else {
                const s = new Set();
                this.root.each(d => { if (!this.isNodeHidden(d)) s.add(d.y); });
                s.delete(0);
                this._guideDepths = [...s];
            }
        }

        ctx.strokeStyle = 'rgba(0, 0, 0, 0.06)';
        ctx.lineWidth = 0.5;
        ctx.setLineDash([4, 4]);

        if (this.layoutMode === 'rectangular') {
            for (const x of this._guideDepths) {
                ctx.beginPath();
                ctx.moveTo(x, -this.cladoBoundsH / 2 - 20);
                ctx.lineTo(x, this.cladoBoundsH / 2 + 20);
                ctx.stroke();
            }
        } else {
            for (const r of this._guideDepths) {
                ctx.beginPath();
                ctx.arc(0, 0, r, 0, Math.PI * 2);
                ctx.stroke();
            }
        }

        ctx.setLineDash([]);
    }

    _drawLink(ctx, source, target) {
        ctx.beginPath();
        if (this.layoutMode === 'rectangular') {
            ctx.moveTo(source.cx, source.cy);
            ctx.lineTo(source.cx, target.cy);
            ctx.lineTo(target.cx, target.cy);
        } else {
            ctx.moveTo(source.cx, source.cy);
            const midAngle = (source.x + target.x) / 2;
            const midR = (source.y + target.y) / 2;
            const midA = (midAngle - 90) * Math.PI / 180;
            const midX = midR * Math.cos(midA);
            const midY = midR * Math.sin(midA);
            ctx.quadraticCurveTo(midX, midY, target.cx, target.cy);
        }
        ctx.stroke();
    }

    drawLinks(ctx) {
        const tcOpts = this.viewDef.tree_chart_options || {};
        const isDiff = this.diffMode && tcOpts.diff_mode;
        const diffColors = isDiff ? tcOpts.diff_mode.colors : null;

        if (!isDiff) {
            ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
            ctx.lineWidth = 0.8;
        }

        this.root.links().forEach(link => {
            if (this.isNodeHidden(link.source) || this.isNodeHidden(link.target)) return;

            if (isDiff) {
                const status = link.target.data._diff_status || 'same';
                const color = diffColors[status] || diffColors.same;
                ctx.strokeStyle = status === 'same' ? 'rgba(0, 0, 0, 0.08)' : color;
                ctx.lineWidth = status === 'same' ? 0.6 : 1.5;
            }

            this._drawLink(ctx, link.source, link.target);
        });

        // Ghost edges: show original parent for "moved" nodes
        if (isDiff && tcOpts.diff_mode.show_ghost_edges) {
            // Build node position map for ghost edge lookup
            const nodeMap = new Map();
            this.root.each(n => nodeMap.set(String(n.id), n));

            ctx.save();
            ctx.setLineDash([4, 4]);
            ctx.strokeStyle = 'rgba(220, 53, 69, 0.3)';
            ctx.lineWidth = 1.0;

            this.root.each(node => {
                if (this.isNodeHidden(node)) return;
                if (node.data._diff_status === 'moved' && node.data._parent_id_a) {
                    const oldParent = nodeMap.get(String(node.data._parent_id_a));
                    if (oldParent && !this.isNodeHidden(oldParent)) {
                        this._drawLink(ctx, oldParent, node);
                    }
                }
            });

            ctx.setLineDash([]);
            ctx.restore();
        }
    }

    drawNodes(ctx, k) {
        const searchIds = new Set(this.searchMatches.map(d => d.id));

        this.root.each(node => {
            if (this.isNodeHidden(node)) return;

            const leaf = this.isLeafByRank(node);
            const isSearch = searchIds.has(node.id);

            let radius = leaf ? 2 : Math.max(3, 6 - node.depth);
            if (isSearch) radius = Math.max(radius, 5);

            ctx.beginPath();
            ctx.arc(node.cx, node.cy, radius, 0, Math.PI * 2);
            ctx.fillStyle = isSearch ? '#ff6b35' : (node._color || '#6c757d');
            ctx.fill();

            if (isSearch) {
                ctx.strokeStyle = '#ff6b35';
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Hover highlight ring
            if (this.hoverNodeId && node.id === this.hoverNodeId) {
                ctx.beginPath();
                ctx.arc(node.cx, node.cy, radius + 5, 0, Math.PI * 2);
                ctx.strokeStyle = '#00bcd4';
                ctx.lineWidth = 2.5;
                ctx.stroke();
            }

            // Collapsed indicator
            if (node._children) {
                ctx.beginPath();
                ctx.arc(node.cx, node.cy, radius + 3, 0, Math.PI * 2);
                ctx.strokeStyle = node._color || '#6c757d';
                ctx.lineWidth = 2;
                ctx.stroke();
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
                const arcThickness = Math.min(node.value / (this.root.value || 1) * 8, 4);
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

    updateLabels(t) {
        if (!this.labelsSvg || !this.root) return;
        this.labelsSvg.style('visibility', 'visible');

        const k = t.k;
        const cx = this.width / 2;
        const cy = this.height / 2;
        const labelKey = this.viewDef.hierarchy_options.label_key || 'name';
        const rankKey = this.viewDef.hierarchy_options.rank_key || 'rank';

        const labelsToShow = [];
        const maxLabels = 500;
        const tcOpts = this.viewDef.tree_chart_options || {};
        const leafRank = tcOpts.leaf_rank;

        // Viewport bounds in data coordinates
        const vpLeft = (-t.x - cx * t.k) / t.k;
        const vpTop = (-t.y - cy * t.k) / t.k;
        const vpRight = vpLeft + this.width / t.k;
        const vpBottom = vpTop + this.height / t.k;

        function isLeafRankFn(node) {
            return leafRank && node.data[rankKey] === leafRank;
        }

        this.root.each(node => {
            if (this.isNodeHidden(node)) return;

            let show = false;
            if (!isLeafRankFn(node)) {
                show = true;
            } else {
                if (k >= 2) {
                    show = node.cx >= vpLeft && node.cx <= vpRight &&
                           node.cy >= vpTop && node.cy <= vpBottom;
                }
            }

            if (show) labelsToShow.push(node);
        });

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
        const sel = this.labelsSvg.selectAll('text')
            .data(limited, d => d.id);

        sel.exit().remove();

        const isRect = this.layoutMode === 'rectangular';

        function isRectLeaf(d) {
            return isLeafRankFn(d) || (!d.children && !d._children);
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
                        return `translate(${sx + labelOffset}, ${sy})`;
                    }
                    return `translate(${sx - labelOffset * 0.5}, ${sy - labelOffset})`;
                }
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
                if (!isLeafRankFn(d)) return 1;
                return Math.min(1, (k - 1.5) * 0.5);
            })
            .text(d => {
                const label = d.data[labelKey] || d.id || '';
                const maxLen = isLeafRankFn(d) ? 20 : 30;
                return label.length > maxLen ? label.substring(0, maxLen) + '...' : label;
            });
    }

    // --- Resize ---

    _onResize() {
        if (!this.viewDef) return;
        if (this.wrapEl.offsetWidth === 0) return;
        this.resizeCanvas();
        if (this.root) {
            this.computeLayout(this.root, this.viewDef);
            this.buildQuadtree(this.root);
            this.render();
        }
    }
}


// --- Backward-compatible entry point ---

async function loadRadialView(viewKey) {
    if (_singletonTC) {
        _singletonTC.destroy();
        _singletonTC = null;
    }

    _singletonTC = new TreeChartInstance({
        wrapEl: document.getElementById('tc-canvas-wrap'),
        toolbarEl: document.getElementById('tc-toolbar'),
        breadcrumbEl: document.getElementById('tc-breadcrumb'),
        tooltipEl: document.getElementById('tc-tooltip'),
        contextMenuEl: document.getElementById('tc-context-menu'),
    });

    await _singletonTC.load(viewKey);
}


// --- Side-by-Side entry point ---

let _sbsLeft = null;
let _sbsRight = null;

async function loadSideBySideView(viewKey) {
    // Destroy previous instances
    if (_sbsLeft) { _sbsLeft.destroy(); _sbsLeft = null; }
    if (_sbsRight) { _sbsRight.destroy(); _sbsRight = null; }

    const view = manifest.views[viewKey];
    if (!view) return;

    // Resolve the base tree chart view key (side_by_side references a tree_chart view)
    const tcOpts = view.tree_chart_options || view.side_by_side_options || {};
    const sourceViewKey = tcOpts.source_view || viewKey;

    // Determine profile IDs
    const leftProfileId = globalControls.profile_id;
    const rightProfileId = globalControls.compare_profile_id;

    // Set panel headers with profile names
    const leftHeader = document.getElementById('sbs-left-header');
    const rightHeader = document.getElementById('sbs-right-header');

    // Fetch profile names for headers
    try {
        const profiles = await fetchQuery('classification_profiles_selector');
        const leftProfile = profiles.find(p => p.id == leftProfileId);
        const rightProfile = profiles.find(p => p.id == rightProfileId);
        if (leftHeader) leftHeader.textContent = leftProfile ? leftProfile.name : `Profile ${leftProfileId}`;
        if (rightHeader) rightHeader.textContent = rightProfile ? rightProfile.name : `Profile ${rightProfileId}`;
    } catch (e) {
        if (leftHeader) leftHeader.textContent = `Profile ${leftProfileId}`;
        if (rightHeader) rightHeader.textContent = `Profile ${rightProfileId}`;
    }

    const sharedContextMenu = document.getElementById('sbs-context-menu');
    const sharedToolbar = document.getElementById('sbs-toolbar');

    // Create left instance (base profile — uses globalControls.profile_id as-is)
    _sbsLeft = new TreeChartInstance({
        wrapEl: document.getElementById('sbs-left-wrap'),
        toolbarEl: sharedToolbar,
        breadcrumbEl: document.getElementById('sbs-left-breadcrumb'),
        tooltipEl: document.getElementById('sbs-left-tooltip'),
        contextMenuEl: sharedContextMenu,
    });

    // Create right instance (compare profile — override profile_id)
    _sbsRight = new TreeChartInstance({
        wrapEl: document.getElementById('sbs-right-wrap'),
        toolbarEl: null,  // toolbar is shared, only left builds it
        breadcrumbEl: document.getElementById('sbs-right-breadcrumb'),
        tooltipEl: document.getElementById('sbs-right-tooltip'),
        contextMenuEl: sharedContextMenu,
        overrideParams: { profile_id: rightProfileId },
    });

    // Load both trees in parallel
    await Promise.all([
        _sbsLeft.load(sourceViewKey),
        _sbsRight.load(sourceViewKey),
    ]);

    // Phase D: sync zoom/pan between instances
    _setupSbsSync(_sbsLeft, _sbsRight);
}

function _setupSbsSync(left, right) {
    if (!left.zoom || !right.zoom) return;

    let syncing = false;

    function syncTransform(source, target) {
        if (syncing) return;
        syncing = true;
        // Directly set transform + render without triggering zoom events
        target.transform = source.transform;
        target.render();
        // Update d3 zoom internal state silently (no events fired)
        target.canvas.__zoom = source.transform;
        syncing = false;
    }

    // Override zoom handlers to add sync
    left.zoom
        .on('start', () => {
            if (syncing) return;
            left._zooming = true;
            left._snapshotCache();
            right._zooming = true;
            right._snapshotCache();
        })
        .on('zoom', (event) => {
            if (syncing) return;
            left.transform = event.transform;
            left.render();
            syncTransform(left, right);
        })
        .on('end', () => {
            if (syncing) return;
            left._zooming = false;
            left._cacheTransform = null;
            left.render();
            left.updateLabels(left.transform || d3.zoomIdentity);
            right._zooming = false;
            right._cacheTransform = null;
            right.render();
            right.updateLabels(right.transform || d3.zoomIdentity);
        });

    right.zoom
        .on('start', () => {
            if (syncing) return;
            right._zooming = true;
            right._snapshotCache();
            left._zooming = true;
            left._snapshotCache();
        })
        .on('zoom', (event) => {
            if (syncing) return;
            right.transform = event.transform;
            right.render();
            syncTransform(right, left);
        })
        .on('end', () => {
            if (syncing) return;
            right._zooming = false;
            right._cacheTransform = null;
            right.render();
            right.updateLabels(right.transform || d3.zoomIdentity);
            left._zooming = false;
            left._cacheTransform = null;
            left.render();
            left.updateLabels(left.transform || d3.zoomIdentity);
        });

    // Sync layout mode: override switchLayout on both
    const origLeftSwitch = left.switchLayout.bind(left);
    const origRightSwitch = right.switchLayout.bind(right);

    left.switchLayout = function(mode) {
        origLeftSwitch(mode);
        if (right.layoutMode !== mode) origRightSwitch(mode);
    };

    right.switchLayout = function(mode) {
        origRightSwitch(mode);
        if (left.layoutMode !== mode) origLeftSwitch(mode);
    };

    // Sync hover highlight
    left.onHoverSync = (nodeId) => right.setHoverNode(nodeId);
    right.onHoverSync = (nodeId) => left.setHoverNode(nodeId);

    // Sync depth toggle
    left.onDepthToggleSync = (hidden) => right.setDepthHidden(hidden);
    right.onDepthToggleSync = (hidden) => left.setDepthHidden(hidden);

    // Sync collapse/expand
    left.onCollapseSync = (nodeId, collapsed) => right.setNodeCollapsed(nodeId, collapsed);
    right.onCollapseSync = (nodeId, collapsed) => left.setNodeCollapsed(nodeId, collapsed);

    // Sync view-as-root (subtree navigation)
    left.onSubtreeSync = (nodeId) => {
        if (nodeId) right.navigateToSubtree(nodeId, true);
        else right.clearSubtreeRoot(true);
    };
    right.onSubtreeSync = (nodeId) => {
        if (nodeId) left.navigateToSubtree(nodeId, true);
        else left.clearSubtreeRoot(true);
    };
}
