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
        script.src = '/static/vendor/d3.v7.min.js';
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
        this.subtreeNode = null;
        this.viewDef = null;
        this.viewKey = null;
        this.transform = null;
        this.quadtree = null;
        this.colorMap = {};
        this.focusNode = null;
        this.searchMatches = [];
        this.canvas = null;
        this.ctx = null;
        this.labelsSvg = null;
        this.zoom = null;
        this.dpr = window.devicePixelRatio || 1;
        this.width = 0;
        this.height = 0;
        this.outerRadius = 0;
        this.textScale = 1.0;
        this.layoutMode = 'radial';
        this.cladoBoundsW = 0;
        this.cladoBoundsH = 0;
        this.contextTarget = null;
        this.hoverNodeId = null;       // ID of hovered node (for cross-instance highlight)
        this.onHoverSync = null;       // callback: (nodeId) => {} for cross-instance hover
        this.onCollapseSync = null;    // callback: (nodeId, collapsed) => {} for cross-instance collapse
        this.onVisibleDepthSync = null; // callback: (depth) => {} for cross-instance depth sync
        this.onSubtreeSync = null;     // callback: (nodeId|null) => {} for cross-instance view-as-root
        this._guideDepths = null;      // cached guide line depths
        this._zooming = false;         // true during active zoom gesture
        this.diffMode = false;         // true when rendering diff tree
        this.diffNodeMap = null;       // Map<nodeId, {cx, cy}> for ghost edges (old parent positions)

        // Unique ID for naming
        this._uid = Math.random().toString(36).slice(2, 8);

        // Rank visibility: ranks ordered root→leaf from rank_radius keys.
        // visibleDepth = number of ranks to show (0 = all, i.e. slider at max).
        // When > 0, ranks beyond this depth from root are hidden (nodes + labels + links).
        this._rankOrder = [];         // e.g. ['Phylum','Class','Order',...,'Genus']
        this.visibleDepth = 0;        // 0 = show all
        this._hiddenRanks = new Set();

        // Watch list: Set of node IDs being watched
        this.watchedNodes = new Set();

        // Removed panel collapse state
        this._removedPanelCollapsed = false;

        // Morph animation state
        this._morphAnimId = null;
        this._morphing = false;
        this._morphBasePositions = null;   // Map<nodeId, {cx, cy, color, r}>
        this._morphComparePositions = null;
        this._morphBaseLinks = null;       // [{sourceId, targetId}, ...]
        this._morphCompareLinks = null;
        this._morphAllNodeIds = null;      // Set of all node IDs in union
        this._morphReversed = false;
        this._morphBaseRoot = null;
        this._morphCompareRoot = null;
        this._morphFullBaseRoot = null;    // full tree roots (preserved for clearSubtreeRoot)
        this._morphFullCompareRoot = null;

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
        // Clean up panels
        const container = this.wrapEl?.closest('.tc-view-content') || this.wrapEl?.parentElement;
        if (container) {
            const wp = container.querySelector('.tc-watch-panel');
            if (wp) wp.remove();
            const rp = container.querySelector('.tc-removed-panel');
            if (rp) rp.remove();
        }
    }

    // --- Main Entry ---

    async load(viewKey, viewDefOverride) {
        this.wrapEl.innerHTML = '<div class="loading">Loading D3.js...</div>';

        try {
            await ensureD3Loaded();
        } catch (e) {
            this.wrapEl.innerHTML = '<div class="text-danger">Failed to load D3.js. Check your internet connection.</div>';
            return;
        }

        // Create canvas + SVG inside wrap
        this.wrapEl.innerHTML = '<canvas></canvas><svg></svg>';

        const view = viewDefOverride || manifest.views[viewKey];
        if (!view) return;

        this.viewDef = view;
        this.viewKey = viewKey;
        this.searchMatches = [];
        this.focusNode = null;
        this.subtreeNode = null;

        const tcOpts = view.tree_chart_options || {};
        this.layoutMode = tcOpts.default_layout || 'radial';

        // Extract rank order from rank_radius (root→leaf, skip _root)
        if (tcOpts.rank_radius) {
            this._rankOrder = Object.keys(tcOpts.rank_radius).filter(k => k !== '_root');
        } else {
            this._rankOrder = [];
        }
        this.visibleDepth = 0;
        this._hiddenRanks = new Set();

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

        this.root = this.fullRoot;
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
        this._updateRemovedPanel();
    }

    // --- Morph Animation ---

    /**
     * Snapshot positions from a d3 hierarchy root.
     * Returns Map<nodeId, {cx, cy, color, r}>.
     */
    snapshotPositions(root) {
        const map = new Map();
        if (!root) return map;
        root.each(n => {
            map.set(String(n.id), {
                cx: n.cx || 0, cy: n.cy || 0,
                x: n.x || 0, y: n.y || 0,
                color: n._color || '#adb5bd',
                r: 8,
            });
        });
        // Also include collapsed children recursively
        function walkCollapsed(node) {
            if (node._children) {
                for (const child of node._children) {
                    if (!map.has(String(child.id))) {
                        // Use parent position as fallback
                        map.set(String(child.id), {
                            cx: node.cx || 0, cy: node.cy || 0,
                            x: node.x || 0, y: node.y || 0,
                            color: node._color || '#adb5bd',
                            r: 0,
                        });
                    }
                    walkCollapsed(child);
                }
            }
            if (node.children) {
                for (const child of node.children) walkCollapsed(child);
            }
        }
        walkCollapsed(root);
        return map;
    }

    /**
     * Capture link list from a d3 hierarchy root.
     * Returns [{sourceId, targetId}, ...]
     */
    snapshotLinks(root) {
        if (!root) return [];
        const links = [];
        root.links().forEach(l => {
            links.push({ sourceId: String(l.source.id), targetId: String(l.target.id) });
        });
        return links;
    }

    /**
     * Load morph view: builds two trees (base + compare) and snapshots their positions.
     * Renders the base tree initially.
     */
    async loadMorph(sourceViewKey, sourceView, baseProfileId, compareProfileId) {
        this.wrapEl.innerHTML = '<canvas></canvas><svg></svg>';

        this.viewDef = sourceView;
        this.viewKey = sourceViewKey;
        this.searchMatches = [];
        this.focusNode = null;
        this.subtreeNode = null;

        const tcOpts = sourceView.tree_chart_options || {};
        this.layoutMode = tcOpts.default_layout || 'radial';

        // Extract rank order from rank_radius
        if (tcOpts.rank_radius) {
            this._rankOrder = Object.keys(tcOpts.rank_radius).filter(k => k !== '_root');
        } else {
            this._rankOrder = [];
        }
        this.visibleDepth = 0;
        this._hiddenRanks = new Set();

        this.canvas = this.wrapEl.querySelector('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.labelsSvg = d3.select(this.wrapEl.querySelector('svg'));
        this.dpr = window.devicePixelRatio || 1;
        this.resizeCanvas();

        if (this.toolbarEl) this.buildToolbar(sourceView);

        // --- Build base tree ---
        this.overrideParams = { profile_id: baseProfileId };
        await this.buildHierarchy(sourceView);
        this.root = this.fullRoot;
        if (!this.root) return;
        this.computeLayout(this.root, sourceView);
        this.assignColors(this.root, sourceView);
        const baseBW = this.cladoBoundsW, baseBH = this.cladoBoundsH;
        this._morphBasePositions = this.snapshotPositions(this.root);
        this._morphBaseLinks = this.snapshotLinks(this.root);
        this._morphBaseRoot = this.root;
        this._morphFullBaseRoot = this.root;  // preserve full tree

        // --- Build compare tree ---
        this.overrideParams = { profile_id: compareProfileId };
        await this.buildHierarchy(sourceView);
        const compareRoot = this.fullRoot;
        if (!compareRoot) return;
        this.computeLayout(compareRoot, sourceView);
        this.assignColors(compareRoot, sourceView);
        // Use max bounds from both trees for fit
        this.cladoBoundsW = Math.max(baseBW, this.cladoBoundsW);
        this.cladoBoundsH = Math.max(baseBH, this.cladoBoundsH);
        this._morphComparePositions = this.snapshotPositions(compareRoot);
        this._morphCompareLinks = this.snapshotLinks(compareRoot);
        this._morphCompareRoot = compareRoot;
        this._morphFullCompareRoot = compareRoot;  // preserve full tree

        // Build union of all node IDs
        this._morphAllNodeIds = new Set([
            ...this._morphBasePositions.keys(),
            ...this._morphComparePositions.keys(),
        ]);

        // Reset to base tree for initial display
        this.root = this._morphBaseRoot;
        this.buildQuadtree(this.root);
        this.setupZoom();
        this.transform = this.computeFitTransform();
        d3.select(this.canvas).call(this.zoom.transform, this.transform);
        this._morphing = true;
        this.renderMorphFrame(0);
        this._updateRemovedPanel();
    }

    /**
     * Render a single morph frame at time t (0 = base, 1 = compare).
     */
    renderMorphFrame(t) {
        if (!this._morphBasePositions || !this._morphComparePositions) return;
        this._morphT = t;  // store current t for re-renders (zoom/pan)

        const fromPos = this._morphReversed ? this._morphComparePositions : this._morphBasePositions;
        const toPos = this._morphReversed ? this._morphBasePositions : this._morphComparePositions;
        const fromLinks = this._morphReversed ? this._morphCompareLinks : this._morphBaseLinks;
        const toLinks = this._morphReversed ? this._morphBaseLinks : this._morphCompareLinks;

        // Easing: cubic ease-in-out
        const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

        // Build set of node IDs hidden by collapse (descendants of collapsed nodes)
        const collapsedHidden = new Set();
        const collectHidden = (root) => {
            if (!root) return;
            root.each(node => {
                if (node._children) {
                    const addDescendants = (children) => {
                        for (const c of children) {
                            collapsedHidden.add(String(c.id));
                            if (c.children) addDescendants(c.children);
                            if (c._children) addDescendants(c._children);
                        }
                    };
                    addDescendants(node._children);
                }
            });
        };
        collectHidden(this._morphBaseRoot);
        collectHidden(this._morphCompareRoot);

        const ctx = this.ctx;
        const dpr = this.dpr;
        const w = this.width;
        const h = this.height;

        ctx.clearRect(0, 0, w * dpr, h * dpr);
        if (this._recordBg) {
            ctx.fillStyle = this._recordBg;
            ctx.fillRect(0, 0, w * dpr, h * dpr);
        }
        ctx.save();

        const tf = this.transform || d3.zoomIdentity;
        const centerX = w / 2;
        const centerY = h / 2;
        ctx.setTransform(tf.k * dpr, 0, 0, tf.k * dpr,
            (tf.x + centerX * tf.k) * dpr,
            (tf.y + centerY * tf.k) * dpr);

        // Build hidden ID set for visible depth filtering (used by edges + nodes)
        const morphHiddenIds = new Set();
        if (this._hiddenRanks.size > 0) {
            const collectHiddenRanks = (root) => {
                if (!root) return;
                root.each(n => { if (this._isRankHidden(n)) morphHiddenIds.add(String(n.id)); });
            };
            collectHiddenRanks(this._morphBaseRoot);
            collectHiddenRanks(this._morphCompareRoot);
        }

        // --- Draw edges ---
        // Build link sets for fast lookup
        const fromLinkSet = new Set(fromLinks.map(l => l.sourceId + '→' + l.targetId));
        const toLinkSet = new Set(toLinks.map(l => l.sourceId + '→' + l.targetId));
        const allLinkKeys = new Set([...fromLinkSet, ...toLinkSet]);

        ctx.lineWidth = 2;
        for (const key of allLinkKeys) {
            const [srcId, tgtId] = key.split('→');
            if (collapsedHidden.has(srcId) || collapsedHidden.has(tgtId)) continue;
            if (morphHiddenIds.has(tgtId)) continue;
            const inFrom = fromLinkSet.has(key);
            const inTo = toLinkSet.has(key);

            // Interpolate source and target positions
            const srcFrom = fromPos.get(srcId);
            const srcTo = toPos.get(srcId);
            const tgtFrom = fromPos.get(tgtId);
            const tgtTo = toPos.get(tgtId);
            if (!srcFrom && !srcTo) continue;
            if (!tgtFrom && !tgtTo) continue;

            const sx = this._lerpVal(srcFrom?.cx, srcTo?.cx, ease, srcFrom?.cx || srcTo?.cx);
            const sy = this._lerpVal(srcFrom?.cy, srcTo?.cy, ease, srcFrom?.cy || srcTo?.cy);
            const tx = this._lerpVal(tgtFrom?.cx, tgtTo?.cx, ease, tgtFrom?.cx || tgtTo?.cx);
            const ty = this._lerpVal(tgtFrom?.cy, tgtTo?.cy, ease, tgtFrom?.cy || tgtTo?.cy);

            let alpha;
            if (inFrom && inTo) alpha = 0.15;           // shared — subtle
            else if (inFrom && !inTo) alpha = 0.15 * Math.max(0, 1 - t * 2);      // fade out in first half (raw t)
            else alpha = 0.15 * Math.max(0, (t - 0.5) * 2);                        // fade in in second half (raw t)

            if (alpha < 0.01) continue;
            ctx.strokeStyle = `rgba(0, 0, 0, ${alpha})`;
            ctx.beginPath();
            ctx.moveTo(sx, sy);
            if (this.layoutMode === 'rectangular') {
                ctx.lineTo(sx, ty);
                ctx.lineTo(tx, ty);
            } else {
                // Radial curved link: interpolate angle/radius for midpoint
                const srcAngle = this._lerpVal(srcFrom?.x, srcTo?.x, ease, srcFrom?.x || srcTo?.x || 0);
                const srcR = this._lerpVal(srcFrom?.y, srcTo?.y, ease, srcFrom?.y || srcTo?.y || 0);
                const tgtAngle = this._lerpVal(tgtFrom?.x, tgtTo?.x, ease, tgtFrom?.x || tgtTo?.x || 0);
                const tgtR = this._lerpVal(tgtFrom?.y, tgtTo?.y, ease, tgtFrom?.y || tgtTo?.y || 0);
                const midAngle = (srcAngle + tgtAngle) / 2;
                const midR = (srcR + tgtR) / 2;
                const midA = (midAngle - 90) * Math.PI / 180;
                const midX = midR * Math.cos(midA);
                const midY = midR * Math.sin(midA);
                ctx.quadraticCurveTo(midX, midY, tx, ty);
            }
            ctx.stroke();
        }

        // --- Draw nodes ---
        const morphSearchIds = new Set(this.searchMatches.map(d => String(d.id)));
        const morphWatchNeighborIds = this._getWatchNeighborIds();

        for (const nodeId of this._morphAllNodeIds) {
            if (collapsedHidden.has(nodeId)) continue;
            if (morphHiddenIds.has(nodeId)) continue;
            const fp = fromPos.get(nodeId);
            const tp = toPos.get(nodeId);
            if (!fp && !tp) continue;

            const cx = this._lerpVal(fp?.cx, tp?.cx, ease, fp?.cx || tp?.cx);
            const cy = this._lerpVal(fp?.cy, tp?.cy, ease, fp?.cy || tp?.cy);

            let r, alpha, color;
            if (fp && tp) {
                // Exists in both: interpolate
                r = fp.r + (tp.r - fp.r) * ease;
                alpha = 1;
                color = this._lerpColor(fp.color, tp.color, ease);
            } else if (fp && !tp) {
                // Removed: fade out in first half of animation (use raw t for linear timing)
                const remT = Math.max(0, 1 - t * 2);  // 1..0 mapped from t 0..0.5
                r = fp.r * remT;
                alpha = remT;
                color = fp.color;
            } else {
                // Added: delayed fade in in second half (use raw t for linear timing)
                const addT = Math.max(0, (t - 0.5) * 2);  // 0..1 mapped from t 0.5..1
                r = tp.r * addT;
                alpha = addT;
                color = tp.color;
            }

            r *= this.textScale;

            // Watch node enlargement
            if (this.watchedNodes.has(nodeId)) {
                r *= 2;
            } else if (morphWatchNeighborIds.has(nodeId)) {
                r *= 1.5;
            }

            const isSearch = morphSearchIds.has(nodeId);
            if (isSearch) {
                r = Math.max(r, 12 * this.textScale);
                color = '#ff6b35';
            }

            if (r < 0.3 || alpha < 0.02) continue;
            ctx.globalAlpha = alpha;
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(cx, cy, Math.max(r, 0.5), 0, 2 * Math.PI);
            ctx.fill();

            // Search highlight ring
            if (isSearch && alpha > 0.1) {
                ctx.strokeStyle = '#ff6b35';
                ctx.lineWidth = 4;
                ctx.stroke();
            }

            // Watch node ring
            if (this.watchedNodes.has(nodeId) && alpha > 0.1) {
                ctx.strokeStyle = '#ffc107';
                ctx.lineWidth = 3;
                ctx.beginPath();
                ctx.arc(cx, cy, Math.max(r, 0.5) + 4, 0, 2 * Math.PI);
                ctx.stroke();
            }
        }

        ctx.globalAlpha = 1;
        ctx.restore();

        // Update active root's node positions to interpolated values
        const activeRoot = (ease < 0.5) ? this._morphBaseRoot : this._morphCompareRoot;
        if (activeRoot && activeRoot !== this.root) this.root = activeRoot;
        if (this.root) {
            this.root.each(n => {
                const nid = String(n.id);
                const fp = fromPos.get(nid);
                const tp = toPos.get(nid);
                if (fp || tp) {
                    n.cx = this._lerpVal(fp?.cx, tp?.cx, ease, fp?.cx || tp?.cx);
                    n.cy = this._lerpVal(fp?.cy, tp?.cy, ease, fp?.cy || tp?.cy);
                    n.x = this._lerpVal(fp?.x, tp?.x, ease, fp?.x || tp?.x);
                    n.y = this._lerpVal(fp?.y, tp?.y, ease, fp?.y || tp?.y);
                }
            });
            // Quadtree only when not animating (for hover/context menu)
            if (!this._morphAnimId) this.buildQuadtree(this.root);
            // Draw labels on canvas (need to re-enter transform)
            ctx.save();
            ctx.setTransform(tf.k * dpr, 0, 0, tf.k * dpr,
                (tf.x + centerX * tf.k) * dpr,
                (tf.y + centerY * tf.k) * dpr);
            this._drawMorphLabels(ctx, fromPos, toPos, t);
            ctx.restore();
        }
        if (this.labelsSvg) this.labelsSvg.style('visibility', 'hidden');
    }

    /**
     * Interpolate a numeric value with fallback for missing endpoints.
     */
    _lerpVal(from, to, t, fallback) {
        if (from != null && to != null) return from + (to - from) * t;
        if (from != null) return from;
        if (to != null) return to;
        return fallback || 0;
    }

    /**
     * Linearly interpolate between two CSS color strings.
     */
    _lerpColor(colorA, colorB, t) {
        const a = this._parseColor(colorA);
        const b = this._parseColor(colorB);
        const r = Math.round(a.r + (b.r - a.r) * t);
        const g = Math.round(a.g + (b.g - a.g) * t);
        const bl = Math.round(a.b + (b.b - a.b) * t);
        return `rgb(${r},${g},${bl})`;
    }

    /**
     * Parse hex or rgb color to {r, g, b}.
     */
    _parseColor(str) {
        if (!str) return { r: 173, g: 181, b: 189 }; // #adb5bd
        if (str.startsWith('#')) {
            let hex = str.slice(1);
            if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
            return {
                r: parseInt(hex.slice(0, 2), 16),
                g: parseInt(hex.slice(2, 4), 16),
                b: parseInt(hex.slice(4, 6), 16),
            };
        }
        const m = str.match(/(\d+)/g);
        if (m && m.length >= 3) return { r: +m[0], g: +m[1], b: +m[2] };
        return { r: 173, g: 181, b: 189 };
    }

    /**
     * Start morph animation loop.
     */
    startMorphAnimation(speed, reversed, onProgress, onDone) {
        this.stopMorphAnimation();
        this._morphReversed = false;  // always interpolate base→compare; direction is handled below

        const duration = 3200 / speed;
        const startT = performance.now();
        // Start from current scrubber position
        const scrubber = document.getElementById('morph-scrubber');
        const startVal = scrubber ? parseInt(scrubber.value, 10) / 1000 : (reversed ? 1 : 0);

        const animate = (now) => {
            const elapsed = now - startT;
            const frac = Math.min(elapsed / duration, 1);
            let t;
            if (reversed) {
                t = Math.max(startVal - startVal * frac, 0);
            } else {
                t = Math.min(startVal + (1 - startVal) * frac, 1);
            }

            this.renderMorphFrame(t);
            if (onProgress) onProgress(t);

            const done = reversed ? (t <= 0) : (t >= 1);
            if (!done) {
                this._morphAnimId = requestAnimationFrame(animate);
            } else {
                this._morphAnimId = null;
                this.renderMorphFrame(reversed ? 0 : 1);
                if (onDone) onDone();
            }
        };
        this._morphAnimId = requestAnimationFrame(animate);
    }

    /**
     * Stop morph animation.
     */
    stopMorphAnimation() {
        if (this._morphAnimId) {
            cancelAnimationFrame(this._morphAnimId);
            this._morphAnimId = null;
        }
    }

    /**
     * Set morph direction (reversed or not).
     */
    setMorphReversed(reversed) {
        this._morphReversed = reversed;
    }

    // --- Data Loading ---

    async buildHierarchy(view) {
        const hOpts = view.hierarchy_options;
        const tcOpts = view.tree_chart_options || {};
        const rows = await fetchQuery(view.source_query, this.overrideParams);

        if (!rows || rows.length === 0) { this.fullRoot = null; return null; }

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
        this.outerRadius = Math.min(this.width, this.height) * 1.68;

        const LEAF_GAP_DEG = 2;
        const SUBTREE_GAP_DEG = 1;
        let nextAngle = 0;
        const hiddenRanks = this._hiddenRanks;

        function layoutRadialSubtree(node) {
            // If this node's rank is hidden, skip entirely
            const rank = node.data[rankKey];
            if (rank && hiddenRanks.has(rank)) return false;

            // Collect visible children (skip hidden-rank subtrees)
            const visibleChildren = [];
            if (node.children) {
                for (const child of node.children) {
                    const childRank = child.data[rankKey];
                    if (!childRank || !hiddenRanks.has(childRank)) {
                        visibleChildren.push(child);
                    }
                }
            }

            if (visibleChildren.length === 0) {
                // This node is now a visible leaf
                node._la = nextAngle;
                nextAngle += node._children ? LEAF_GAP_DEG * 2 : LEAF_GAP_DEG;
                return true;
            }
            let placed = 0;
            for (let i = 0; i < visibleChildren.length; i++) {
                const ok = layoutRadialSubtree(visibleChildren[i]);
                if (ok && i < visibleChildren.length - 1) {
                    nextAngle += SUBTREE_GAP_DEG;
                }
                if (ok) placed++;
            }
            if (placed === 0) {
                node._la = nextAngle;
                nextAngle += LEAF_GAP_DEG;
                return true;
            }
            const first = visibleChildren[0];
            const last = visibleChildren[visibleChildren.length - 1];
            node._la = (first._la + last._la) / 2;
            return true;
        }

        layoutRadialSubtree(root);

        const totalAngle = nextAngle || 1;
        root.each(node => {
            node.x = (node._la / totalAngle) * 360;
            node.y = node.depth * (this.outerRadius / (root.height || 1));
        });

        // Align same-rank nodes to the same radius
        const rankRadius = tcOpts.rank_radius;
        if (rankRadius) {
            root.each(node => {
                const rank = node.data[rankKey];
                if (rank && rankRadius[rank] !== undefined) {
                    node.y = rankRadius[rank] * this.outerRadius;
                }
            });
        } else {
            // Auto-align: compute average depth per rank, then assign evenly spaced radii
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
            if (ranks.length > 1) {
                const rankY = {};
                ranks.forEach((rank, i) => {
                    rankY[rank] = (i / (ranks.length - 1)) * this.outerRadius;
                });
                root.each(node => {
                    const rank = node.data[rankKey];
                    if (rank && rankY[rank] !== undefined) {
                        node.y = rankY[rank];
                    }
                });
            }
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

        const LEAF_GAP = 12;
        const SUBTREE_GAP = 16;
        let nextY = 0;
        const hiddenRanksClado = this._hiddenRanks;

        function layoutSubtree(node) {
            const rank = node.data[rankKey];
            if (rank && hiddenRanksClado.has(rank)) return false;

            const visibleChildren = [];
            if (node.children) {
                for (const child of node.children) {
                    const childRank = child.data[rankKey];
                    if (!childRank || !hiddenRanksClado.has(childRank)) {
                        visibleChildren.push(child);
                    }
                }
            }

            if (visibleChildren.length === 0) {
                node._ly = nextY;
                nextY += node._children ? LEAF_GAP * 2 : LEAF_GAP;
                return true;
            }
            let placed = 0;
            for (let i = 0; i < visibleChildren.length; i++) {
                const ok = layoutSubtree(visibleChildren[i]);
                if (ok && i < visibleChildren.length - 1) {
                    nextY += SUBTREE_GAP;
                }
                if (ok) placed++;
            }
            if (placed === 0) {
                node._ly = nextY;
                nextY += LEAF_GAP;
                return true;
            }
            const first = visibleChildren[0];
            const last = visibleChildren[visibleChildren.length - 1];
            node._ly = (first._ly + last._ly) / 2;
            return true;
        }

        layoutSubtree(root);

        const treeH = Math.max(nextY, LEAF_GAP);
        const depthSpacing = 120;
        const maxDepth = root.height || 1;

        root.each(node => {
            node.x = node._ly;
            node.y = node.depth * depthSpacing;
        });

        // Align same-rank nodes to the same fixed Y position.
        // Use depthSpacing * rank_index so spacing stays consistent regardless of subtree depth.
        const rankRadius = tcOpts.rank_radius;
        if (rankRadius) {
            // rank_radius values are 0..1 fractions; find min/max among ranks present in this tree
            const presentRanks = new Set();
            root.each(node => {
                const rank = node.data[rankKey];
                if (rank && rankRadius[rank] !== undefined) presentRanks.add(rank);
            });
            // Map fraction range to depthSpacing-based positions
            const fractions = [...presentRanks].map(r => rankRadius[r]);
            const minF = Math.min(...fractions);
            const maxF = Math.max(...fractions);
            const rangeF = maxF - minF || 1;
            const totalW = presentRanks.size * depthSpacing;
            root.each(node => {
                const rank = node.data[rankKey];
                if (rank && rankRadius[rank] !== undefined) {
                    node.y = ((rankRadius[rank] - minF) / rangeF) * totalW;
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
            const totalW = ranks.length * depthSpacing;
            const rankY = {};
            ranks.forEach((rank, i) => {
                rankY[rank] = (ranks.length > 1) ? (i / (ranks.length - 1)) * totalW : 0;
            });
            root.each(node => {
                const rank = node.data[rankKey];
                if (rank && rankY[rank] !== undefined) {
                    node.y = rankY[rank];
                }
            });
        }

        // Compute actual treeW from node positions
        let treeW = 0;
        root.each(node => { if (node.y > treeW) treeW = node.y; });
        treeW = Math.max(treeW, depthSpacing);

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
        // Canvas render applies: translate(t.x + cx*t.k, t.y + cy*t.k) then scale(t.k)
        // For data origin (0,0) to land at canvas center (cx, cy):
        //   t.x + cx*t.k = cx  →  t.x = cx*(1-k)
        //   t.y + cy*t.k = cy  →  t.y = cy*(1-k)
        const cx = this.width / 2;
        const cy = this.height / 2;
        let fitScale;

        if (this.layoutMode === 'rectangular') {
            const padding = 120;
            const scaleX = this.width / (this.cladoBoundsW + padding);
            const scaleY = this.height / (this.cladoBoundsH + padding);
            fitScale = Math.min(scaleX, scaleY, 1);
        } else {
            const margin = 0.1; // 10% margin for labels
            fitScale = Math.min(this.width, this.height) * (1 - margin * 2) / (2 * this.outerRadius);
            fitScale = Math.min(fitScale, 1);
        }

        return d3.zoomIdentity
            .translate(cx * (1 - fitScale), cy * (1 - fitScale))
            .scale(fitScale);
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

        // Text size buttons
        html += `<span class="tc-radius-scale">
            <button class="tc-text-smaller" title="Smaller text"><i class="bi bi-fonts"></i>−</button>
            <button class="tc-text-larger" title="Larger text"><i class="bi bi-fonts"></i>+</button>
        </span>`;

        // Reset zoom
        html += '<button class="tc-reset-btn" title="Reset zoom"><i class="bi bi-arrows-fullscreen"></i></button>';

        // Settings gear popup (always rendered; contains layout+text for mobile, depth slider if multi-rank)
        {
            const maxDepth = this._rankOrder.length;
            let popupContent = '';

            // Layout section (hidden on desktop via CSS, shown on mobile)
            popupContent += `<div class="tc-settings-section tc-popup-layout">
                <div class="tc-settings-title">Layout</div>
                <div class="tc-settings-row">
                    <button class="tc-layout-btn tc-layout-radial${radialActive}" title="Radial layout"><i class="bi bi-bullseye"></i> Radial</button>
                    <button class="tc-layout-btn tc-layout-rect${rectActive}" title="Rectangular layout"><i class="bi bi-diagram-3"></i> Rect</button>
                </div>
            </div>`;

            // Text size section (hidden on desktop via CSS, shown on mobile)
            popupContent += `<div class="tc-settings-section tc-popup-text">
                <div class="tc-settings-title">Text size</div>
                <div class="tc-settings-row">
                    <button class="tc-text-smaller" title="Smaller text"><i class="bi bi-fonts"></i>−</button>
                    <button class="tc-text-larger" title="Larger text"><i class="bi bi-fonts"></i>+</button>
                </div>
            </div>`;

            // Depth slider (only if multiple ranks)
            if (maxDepth > 1) {
                popupContent += `<div class="tc-settings-section">
                    <div class="tc-settings-title">Visible depth</div>
                    <input type="range" class="tc-depth-slider" min="1" max="${maxDepth}" value="${this.visibleDepth || maxDepth}" step="1">
                    <div class="tc-depth-label">${this.visibleDepth ? `→ ${this._rankOrder[this.visibleDepth - 1]}` : `All (${this._rankOrder[this._rankOrder.length - 1] || ''})`}</div>
                </div>`;
            }

            html += `<span class="tc-settings-wrap" style="position:relative">
                <button class="tc-settings-btn" title="Display settings"><i class="bi bi-gear"></i></button>
                <div class="tc-settings-popup" style="display:none">${popupContent}</div>
            </span>`;
        }

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

        // Event: layout toggle (bind all instances: toolbar + popup)
        toolbar.querySelectorAll('.tc-layout-radial').forEach(btn =>
            btn.addEventListener('click', () => this.switchLayout('radial')));
        toolbar.querySelectorAll('.tc-layout-rect').forEach(btn =>
            btn.addEventListener('click', () => this.switchLayout('rectangular')));


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

        // Event: text size buttons (bind all instances: toolbar + popup)
        const applyTextScale = (val) => {
            val = Math.round(val * 10) / 10;
            val = Math.max(0.3, Math.min(5, val));
            this.setTextScale(val);
            if (this.onTextScaleSync) this.onTextScaleSync(val);
        };

        toolbar.querySelectorAll('.tc-text-smaller').forEach(btn =>
            btn.addEventListener('click', () => applyTextScale(this.textScale - 0.1)));
        toolbar.querySelectorAll('.tc-text-larger').forEach(btn =>
            btn.addEventListener('click', () => applyTextScale(this.textScale + 0.1)));

        // Event: keyboard shortcut for text scale ([ = smaller, ] = larger)
        const keyHandler = (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            if (e.key === '[') applyTextScale(this.textScale - 0.1);
            else if (e.key === ']') applyTextScale(this.textScale + 0.1);
        };
        document.addEventListener('keydown', keyHandler);

        // Event: settings gear popup with depth slider
        const settingsBtn = toolbar.querySelector('.tc-settings-btn');
        const settingsPopup = toolbar.querySelector('.tc-settings-popup');
        if (settingsBtn && settingsPopup) {
            settingsBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                settingsPopup.style.display = settingsPopup.style.display === 'none' ? 'block' : 'none';
            });
            document.addEventListener('click', (e) => {
                if (!settingsPopup.contains(e.target) && e.target !== settingsBtn) {
                    settingsPopup.style.display = 'none';
                }
            });
            const slider = settingsPopup.querySelector('.tc-depth-slider');
            const label = settingsPopup.querySelector('.tc-depth-label');
            if (slider) {
                slider.addEventListener('input', () => {
                    const val = parseInt(slider.value);
                    const maxDepth = this._rankOrder.length;
                    this.setVisibleDepth(val >= maxDepth ? 0 : val);
                    label.textContent = this.visibleDepth
                        ? `→ ${this._rankOrder[this.visibleDepth - 1]}`
                        : `All (${this._rankOrder[this._rankOrder.length - 1] || ''})`;
                    if (this.onVisibleDepthSync) this.onVisibleDepthSync(this.visibleDepth);
                });
            }
        }
    }

    switchLayout(mode) {
        if (mode === this.layoutMode) return;
        this.layoutMode = mode;

        // Update button active states (toolbar + popup)
        if (this.toolbarEl) {
            this.toolbarEl.querySelectorAll('.tc-layout-radial').forEach(btn => btn.classList.toggle('active', mode === 'radial'));
            this.toolbarEl.querySelectorAll('.tc-layout-rect').forEach(btn => btn.classList.toggle('active', mode === 'rectangular'));
        }

        if (this.root) {
            if (this._morphing) {
                // Re-layout and re-snapshot both morph trees for new layout mode
                const view = this.viewDef;
                this.computeLayout(this._morphBaseRoot, view);
                const baseBW = this.cladoBoundsW, baseBH = this.cladoBoundsH;
                this._morphBasePositions = this.snapshotPositions(this._morphBaseRoot);
                this._morphBaseLinks = this.snapshotLinks(this._morphBaseRoot);

                this.computeLayout(this._morphCompareRoot, view);
                // Use max bounds from both trees for fit
                this.cladoBoundsW = Math.max(baseBW, this.cladoBoundsW);
                this.cladoBoundsH = Math.max(baseBH, this.cladoBoundsH);
                this._morphComparePositions = this.snapshotPositions(this._morphCompareRoot);
                this._morphCompareLinks = this.snapshotLinks(this._morphCompareRoot);

                this.buildQuadtree(this.root);
                this.transform = this.computeFitTransform();
                d3.select(this.canvas).call(this.zoom.transform, this.transform);
                this.renderMorphFrame(this._morphT || 0);
            } else {
                this.computeLayout(this.root, this.viewDef);
                this.buildQuadtree(this.root);
                this.transform = this.computeFitTransform();
                d3.select(this.canvas).call(this.zoom.transform, this.transform);
                this.render();
            }
        }
    }

    /**
     * Set visible depth: 0 = show all, N = show only first N ranks (root→leaf).
     * Ranks beyond depth N are hidden (nodes, labels, links).
     */
    setVisibleDepth(depth) {
        this.visibleDepth = depth;
        this._hiddenRanks = new Set();
        if (depth > 0 && this._rankOrder.length > 0) {
            for (let i = depth; i < this._rankOrder.length; i++) {
                this._hiddenRanks.add(this._rankOrder[i]);
            }
        }
        // Update slider if toolbar exists
        if (this.toolbarEl) {
            const slider = this.toolbarEl.querySelector('.tc-depth-slider');
            const label = this.toolbarEl.querySelector('.tc-depth-label');
            if (slider) slider.value = depth || this._rankOrder.length;
            if (label) label.textContent = depth
                ? `→ ${this._rankOrder[depth - 1]}`
                : `All (${this._rankOrder[this._rankOrder.length - 1] || ''})`;
        }
        // Re-layout so visible leaf nodes redistribute evenly
        if (this._morphing) {
            if (this._morphBaseRoot) this.computeLayout(this._morphBaseRoot, this.viewDef);
            if (this._morphCompareRoot) this.computeLayout(this._morphCompareRoot, this.viewDef);
            this._morphBasePositions = this._morphBaseRoot ? this.snapshotPositions(this._morphBaseRoot) : null;
            this._morphComparePositions = this._morphCompareRoot ? this.snapshotPositions(this._morphCompareRoot) : null;
            this._morphBaseLinks = this._morphBaseRoot ? this.snapshotLinks(this._morphBaseRoot) : null;
            this._morphCompareLinks = this._morphCompareRoot ? this.snapshotLinks(this._morphCompareRoot) : null;
            this.renderMorphFrame(this._morphT || 0);
        } else if (this.root) {
            this.computeLayout(this.root, this.viewDef);
            this.buildQuadtree(this.root);
            this.render();
        }
    }

    /** Check if a node's rank is hidden by the visible depth setting. */
    _isRankHidden(node) {
        if (this._hiddenRanks.size === 0) return false;
        const rankKey = (this.viewDef && this.viewDef.hierarchy_options)
            ? this.viewDef.hierarchy_options.rank_key || 'rank' : 'rank';
        return this._hiddenRanks.has(node.data[rankKey]);
    }

    setTextScale(val) {
        this.textScale = val;
        if (!this.root) return;

        if (this._morphing) {
            this.renderMorphFrame(this._morphT || 0);
        } else {
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

        // In morph mode, search both base and compare trees to find all matches
        if (this._morphing && this._morphBaseRoot && this._morphCompareRoot) {
            const seen = new Set();
            for (const r of [this._morphBaseRoot, this._morphCompareRoot]) {
                r.each(d => {
                    const nid = String(d.id);
                    if (seen.has(nid)) return;
                    const label = (d.data[labelKey] || '').toLowerCase();
                    if (label.includes(lower)) {
                        seen.add(nid);
                        this.searchMatches.push(d);
                    }
                });
            }
        } else {
            this.root.each(d => {
                const label = (d.data[labelKey] || '').toLowerCase();
                if (label.includes(lower)) {
                    this.searchMatches.push(d);
                }
            });
        }

        if (this.searchMatches.length > 0) {
            // In morph mode, update match positions to current interpolated values
            if (this._morphing) {
                const fromPos = this._morphReversed ? this._morphComparePositions : this._morphBasePositions;
                const toPos = this._morphReversed ? this._morphBasePositions : this._morphComparePositions;
                const mt = this._morphT || 0;
                const ease = mt < 0.5 ? 4 * mt * mt * mt : 1 - Math.pow(-2 * mt + 2, 3) / 2;
                for (const m of this.searchMatches) {
                    const nid = String(m.id);
                    const fp = fromPos.get(nid);
                    const tp = toPos.get(nid);
                    if (fp || tp) {
                        m.cx = this._lerpVal(fp?.cx, tp?.cx, ease, fp?.cx || tp?.cx);
                        m.cy = this._lerpVal(fp?.cy, tp?.cy, ease, fp?.cy || tp?.cy);
                    }
                }
            }
            this.zoomToFitNodes(this.searchMatches);
        }

        this.render();
    }

    // --- Watch ---

    toggleWatch(nodeId) {
        const nid = String(nodeId);
        if (this.watchedNodes.has(nid)) {
            this.watchedNodes.delete(nid);
        } else {
            this.watchedNodes.add(nid);
        }
        this._updateWatchPanel();
        this.render();
    }

    _getWatchNeighborIds() {
        const neighbors = new Set();
        if (this.watchedNodes.size === 0) return neighbors;

        const roots = [];
        if (this._morphing && this._morphBaseRoot && this._morphCompareRoot) {
            roots.push(this._morphBaseRoot, this._morphCompareRoot);
        } else if (this.root) {
            roots.push(this.root);
        }

        for (const r of roots) {
            r.each(node => {
                const nid = String(node.id);
                if (!this.watchedNodes.has(nid)) return;
                // Parent
                if (node.parent) neighbors.add(String(node.parent.id));
                // Children
                const children = node.children || node._children;
                if (children) {
                    for (const c of children) neighbors.add(String(c.id));
                }
            });
        }

        // Don't include watched nodes themselves as neighbors
        for (const w of this.watchedNodes) neighbors.delete(w);
        return neighbors;
    }

    _findNodeById(nodeId) {
        const nid = String(nodeId);
        let found = null;
        if (this._morphing && this._morphBaseRoot && this._morphCompareRoot) {
            for (const r of [this._morphBaseRoot, this._morphCompareRoot]) {
                r.each(d => { if (String(d.id) === nid && !found) found = d; });
                if (found) return found;
            }
        } else if (this.root) {
            this.root.each(d => { if (String(d.id) === nid && !found) found = d; });
        }
        return found;
    }

    _updateWatchPanel() {
        // Find or create the watch panel container inside wrapEl's parent
        const container = this.wrapEl?.closest('.tc-view-content') || this.wrapEl?.parentElement;
        if (!container) return;

        let panel = container.querySelector('.tc-watch-panel');
        if (this.watchedNodes.size === 0) {
            if (panel) panel.remove();
            return;
        }

        if (!panel) {
            panel = document.createElement('div');
            panel.className = 'tc-watch-panel';
            container.appendChild(panel);
        }

        const labelKey = this.viewDef?.hierarchy_options?.label_key || 'name';
        let html = '<div class="tc-watch-header"><i class="bi bi-eye"></i> Watch</div>';

        for (const nid of this.watchedNodes) {
            const node = this._findNodeById(nid);
            const label = node ? (node.data[labelKey] || nid) : nid;
            html += `<div class="tc-watch-item" data-nid="${nid}">
                <span class="tc-watch-label">${label}</span>
                <span class="tc-watch-remove" data-nid="${nid}">&times;</span>
            </div>`;
        }
        panel.innerHTML = html;

        // Bind events
        panel.querySelectorAll('.tc-watch-label').forEach(el => {
            el.addEventListener('click', () => {
                const nid = el.parentElement.dataset.nid;
                const node = this._findNodeById(nid);
                if (node) this.zoomToNode(node, 4);
            });
        });
        panel.querySelectorAll('.tc-watch-remove').forEach(el => {
            el.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleWatch(el.dataset.nid);
            });
        });

        // Reposition removed panel below watch panel
        this._repositionRemovedPanel();
    }

    _repositionRemovedPanel() {
        const container = this.wrapEl?.closest('.tc-view-content') || this.wrapEl?.parentElement;
        if (!container) return;
        const removedPanel = container.querySelector('.tc-removed-panel');
        if (!removedPanel) return;
        const watchPanel = container.querySelector('.tc-watch-panel');
        if (watchPanel) {
            removedPanel.style.top = (watchPanel.offsetTop + watchPanel.offsetHeight + 8) + 'px';
        } else {
            removedPanel.style.top = '50px';
        }
    }

    _updateRemovedPanel() {
        const container = this.wrapEl?.closest('.tc-view-content') || this.wrapEl?.parentElement;
        if (!container) return;

        let panel = container.querySelector('.tc-removed-panel');

        // Only show in diff mode or morph mode
        const showPanel = this.diffMode || this._morphing;
        if (!showPanel) {
            if (panel) panel.remove();
            return;
        }

        const labelKey = this.viewDef?.hierarchy_options?.label_key || 'name';
        const removedNodes = [];

        if (this._morphing && this._morphBasePositions && this._morphComparePositions) {
            // Nodes in base but not in compare = removed
            const fromPos = this._morphReversed ? this._morphComparePositions : this._morphBasePositions;
            const toPos = this._morphReversed ? this._morphBasePositions : this._morphComparePositions;
            const baseRoot = this._morphReversed ? this._morphCompareRoot : this._morphBaseRoot;
            if (baseRoot) {
                baseRoot.each(node => {
                    const nid = String(node.id);
                    if (fromPos.has(nid) && !toPos.has(nid)) {
                        removedNodes.push({ id: nid, label: node.data[labelKey] || nid });
                    }
                });
            }
        } else if (this.diffMode && this.root) {
            this.root.each(node => {
                if (node.data._diff_status === 'removed') {
                    removedNodes.push({ id: String(node.id), label: node.data[labelKey] || String(node.id) });
                }
            });
        }

        if (removedNodes.length === 0) {
            if (panel) panel.remove();
            return;
        }

        if (!panel) {
            panel = document.createElement('div');
            panel.className = 'tc-removed-panel';
            container.appendChild(panel);
        }

        const chevron = this._removedPanelCollapsed ? 'bi-chevron-up' : 'bi-chevron-down';
        let html = `<div class="tc-removed-header">
            <span><i class="bi bi-dash-circle"></i> Removed (${removedNodes.length})</span>
            <i class="bi ${chevron} tc-removed-collapse-icon"></i>
        </div>`;
        for (const n of removedNodes) {
            html += `<div class="tc-removed-item" data-nid="${n.id}">
                <span class="tc-removed-label">${n.label}</span>
            </div>`;
        }
        panel.innerHTML = html;

        // Apply collapsed state
        if (this._removedPanelCollapsed) panel.classList.add('collapsed');
        else panel.classList.remove('collapsed');

        // Header click: toggle collapse
        panel.querySelector('.tc-removed-header').addEventListener('click', () => {
            this._removedPanelCollapsed = !this._removedPanelCollapsed;
            panel.classList.toggle('collapsed', this._removedPanelCollapsed);
            const icon = panel.querySelector('.tc-removed-collapse-icon');
            if (icon) icon.className = `bi ${this._removedPanelCollapsed ? 'bi-chevron-up' : 'bi-chevron-down'} tc-removed-collapse-icon`;
        });

        // Position below watch panel if it exists
        const watchPanel = container.querySelector('.tc-watch-panel');
        if (watchPanel) {
            const watchBottom = watchPanel.offsetTop + watchPanel.offsetHeight + 8;
            panel.style.top = watchBottom + 'px';
        } else {
            panel.style.top = '50px';
        }

        // Click to zoom
        panel.querySelectorAll('.tc-removed-label').forEach(el => {
            el.addEventListener('click', () => {
                const nid = el.parentElement.dataset.nid;
                const node = this._findNodeById(nid);
                if (node) this.zoomToNode(node, 4);
            });
        });
    }

    // --- Zoom ---

    setupZoom() {
        this.zoom = d3.zoom()
            .scaleExtent([0.001, 100])
            .on('start', () => {
                this._zooming = true;
            })
            .on('zoom', (event) => {
                this.transform = event.transform;
                this.render();
            })
            .on('end', () => {
                this._zooming = false;
                this.render();
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
        // Render applies: translate(t.x + cx*t.k, t.y + cy*t.k), scale(t.k)
        // To place node at canvas center: t.x + cx*k + node.cx*k = cx
        //   → t.x = cx*(1-k) - k*node.cx
        const transform = d3.zoomIdentity
            .translate(cx, cy)
            .scale(scale)
            .translate(-cx - node.cx, -cy - node.cy);

        d3.select(this.canvas)
            .transition().duration(600)
            .call(this.zoom.transform, transform);
    }

    zoomToFitNodes(nodes) {
        if (!nodes || nodes.length === 0 || !this.zoom) return;
        const cx = this.width / 2;
        const cy = this.height / 2;

        // Compute bounding box of all nodes
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        for (const n of nodes) {
            if (n.cx < minX) minX = n.cx;
            if (n.cx > maxX) maxX = n.cx;
            if (n.cy < minY) minY = n.cy;
            if (n.cy > maxY) maxY = n.cy;
        }

        const bboxW = maxX - minX;
        const bboxH = maxY - minY;
        const bboxCx = (minX + maxX) / 2;
        const bboxCy = (minY + maxY) / 2;

        // Scale to fit with padding
        const padding = 100;
        let scale;
        if (bboxW < 1 && bboxH < 1) {
            // Single node or very tight cluster
            scale = 4;
        } else {
            const scaleX = (this.width - padding) / bboxW;
            const scaleY = (this.height - padding) / bboxH;
            scale = Math.min(scaleX, scaleY, 10);
        }
        scale = Math.max(scale, 0.1);

        const transform = d3.zoomIdentity
            .translate(cx, cy)
            .scale(scale)
            .translate(-cx - bboxCx, -cy - bboxCy);

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
            if (!this._zooming && !this._morphing) this.render();
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

        // Collapsed internal node → expand (takes priority over leaf check)
        if (nearest._children) {
            this.toggleNode(nearest);
            return;
        }

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
        this._updateRemovedPanel();

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

        // "Watch / Unwatch"
        const nid = String(node.id);
        if (this.watchedNodes.has(nid)) {
            addItem('bi-eye-slash', 'Unwatch', () => this.toggleWatch(nid));
        } else {
            addItem('bi-eye', 'Watch', () => this.toggleWatch(nid));
        }

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
        // Morph mode: rebuild morph data for subtree
        if (this._morphing) {
            this.stopMorphAnimation();
            this._navigateMorphSubtree(nodeId);
            if (this.breadcrumbEl) this.updateBreadcrumb();
            if (!_fromSync && this.onSubtreeSync) this.onSubtreeSync(nodeId);
            return;
        }

        const sourceTree = this.fullRoot;

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
        this._updateRemovedPanel();
        if (this.breadcrumbEl) this.updateBreadcrumb();

        if (!_fromSync && this.onSubtreeSync) this.onSubtreeSync(nodeId);
    }

    /**
     * Navigate to subtree while preserving morph mode.
     * Rebuilds morph data (positions/links) from both base and compare subtrees.
     */
    _navigateMorphSubtree(nodeId) {
        // Find target node in base root
        let baseTarget = null;
        this._morphBaseRoot.each(d => { if (d.id === nodeId) baseTarget = d; });

        // Find target node in compare root
        let compareTarget = null;
        this._morphCompareRoot.each(d => { if (d.id === nodeId) compareTarget = d; });

        // At least one must exist and not be a leaf
        const target = baseTarget || compareTarget;
        if (!target || this.isLeafByRank(target)) return;
        this.subtreeNode = target;

        // Build subtree from base root
        let subBaseBW = 0, subBaseBH = 0;
        if (baseTarget) {
            const baseSubtree = this.buildSubtreeFromNode(baseTarget);
            if (baseSubtree) {
                this.computeLayout(baseSubtree, this.viewDef);
                subBaseBW = this.cladoBoundsW; subBaseBH = this.cladoBoundsH;
                this.assignColors(baseSubtree, this.viewDef);
                this._morphBasePositions = this.snapshotPositions(baseSubtree);
                this._morphBaseLinks = this.snapshotLinks(baseSubtree);
                this._morphBaseRoot = baseSubtree;
            }
        } else {
            // Node doesn't exist in base — empty
            this._morphBasePositions = new Map();
            this._morphBaseLinks = [];
        }

        // Build subtree from compare root
        if (compareTarget) {
            const compareSubtree = this.buildSubtreeFromNode(compareTarget);
            if (compareSubtree) {
                this.computeLayout(compareSubtree, this.viewDef);
                this.assignColors(compareSubtree, this.viewDef);
                this._morphComparePositions = this.snapshotPositions(compareSubtree);
                this._morphCompareLinks = this.snapshotLinks(compareSubtree);
                this._morphCompareRoot = compareSubtree;
            }
        } else {
            this._morphComparePositions = new Map();
            this._morphCompareLinks = [];
        }
        // Use max bounds from both subtrees
        this.cladoBoundsW = Math.max(subBaseBW, this.cladoBoundsW);
        this.cladoBoundsH = Math.max(subBaseBH, this.cladoBoundsH);

        // Rebuild node ID union
        this._morphAllNodeIds = new Set([
            ...this._morphBasePositions.keys(),
            ...this._morphComparePositions.keys(),
        ]);

        // Reset to base tree, fit zoom, render at current scrubber position
        this.root = this._morphBaseRoot || this._morphCompareRoot;
        this.buildQuadtree(this.root);
        this.transform = this.computeFitTransform();
        d3.select(this.canvas).call(this.zoom.transform, this.transform);

        const scrubber = document.getElementById('morph-scrubber');
        const t = scrubber ? parseInt(scrubber.value, 10) / 1000 : 0;
        this.renderMorphFrame(t);
        this._updateRemovedPanel();
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

        if (this._morphing) {
            this.stopMorphAnimation();
            this._rebuildMorphFromFullTree();
            if (this.breadcrumbEl) this.updateBreadcrumb();
            if (!_fromSync && this.onSubtreeSync) this.onSubtreeSync(null);
            return;
        }

        this.root = this.fullRoot;
        this.computeLayout(this.root, this.viewDef);
        this.assignColors(this.root, this.viewDef);
        this.buildQuadtree(this.root);
        this.transform = this.computeFitTransform();
        d3.select(this.canvas).call(this.zoom.transform, this.transform);
        this.render();
        this._updateRemovedPanel();
        if (this.breadcrumbEl) this.updateBreadcrumb();

        if (!_fromSync && this.onSubtreeSync) this.onSubtreeSync(null);
    }

    /**
     * Rebuild morph data from full trees (when clearing subtree root).
     */
    _rebuildMorphFromFullTree() {
        // Rebuild base
        const baseRoot = this._morphBaseRoot;
        // Walk up to find full root
        let baseFullRoot = baseRoot;
        while (baseFullRoot.parent) baseFullRoot = baseFullRoot.parent;

        let compareFullRoot = this._morphCompareRoot;
        while (compareFullRoot.parent) compareFullRoot = compareFullRoot.parent;

        // Need to re-fetch full trees from stored data — simplest: use loadMorph's stored full roots
        // But we didn't store them. Instead, rebuild from fullRoot data.
        // Actually, the full roots were modified during subtree navigation. We need the originals.
        // Store full roots on first loadMorph.
        let clearBaseBW = 0, clearBaseBH = 0;
        if (this._morphFullBaseRoot) {
            this._morphBaseRoot = this._morphFullBaseRoot;
            this.computeLayout(this._morphBaseRoot, this.viewDef);
            clearBaseBW = this.cladoBoundsW; clearBaseBH = this.cladoBoundsH;
            this.assignColors(this._morphBaseRoot, this.viewDef);
            this._morphBasePositions = this.snapshotPositions(this._morphBaseRoot);
            this._morphBaseLinks = this.snapshotLinks(this._morphBaseRoot);
        }
        if (this._morphFullCompareRoot) {
            this._morphCompareRoot = this._morphFullCompareRoot;
            this.computeLayout(this._morphCompareRoot, this.viewDef);
            this.assignColors(this._morphCompareRoot, this.viewDef);
            this._morphComparePositions = this.snapshotPositions(this._morphCompareRoot);
            this._morphCompareLinks = this.snapshotLinks(this._morphCompareRoot);
        }
        this.cladoBoundsW = Math.max(clearBaseBW, this.cladoBoundsW);
        this.cladoBoundsH = Math.max(clearBaseBH, this.cladoBoundsH);

        this._morphAllNodeIds = new Set([
            ...this._morphBasePositions.keys(),
            ...this._morphComparePositions.keys(),
        ]);

        this.root = this._morphBaseRoot;
        this.buildQuadtree(this.root);
        this.transform = this.computeFitTransform();
        d3.select(this.canvas).call(this.zoom.transform, this.transform);

        const scrubber = document.getElementById('morph-scrubber');
        const t = scrubber ? parseInt(scrubber.value, 10) / 1000 : 0;
        this.renderMorphFrame(t);
        this._updateRemovedPanel();
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

    render() {
        // In morph mode, delegate to morph renderer
        if (this._morphing && this._morphBasePositions) {
            this.renderMorphFrame(this._morphT != null ? this._morphT : 0);
            return;
        }
        if (!this.ctx || !this.root) return;

        const ctx = this.ctx;
        const t = this.transform || d3.zoomIdentity;

        const cx = this.width / 2;
        const cy = this.height / 2;

        ctx.clearRect(0, 0, this.width, this.height);
        ctx.save();
        ctx.translate(t.x + cx * t.k, t.y + cy * t.k);
        ctx.scale(t.k, t.k);

        this.drawGuideLines(ctx);
        this.drawLinks(ctx);
        this.drawNodes(ctx);
        this.drawLabels(ctx);

        ctx.restore();

        if (this.diffMode) this.drawDiffLegend(ctx);
        if (this.labelsSvg) this.labelsSvg.style('visibility', 'hidden');
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

        const lineH = 18, padX = 12, padY = 8;
        const boxW = 170, boxH = padY * 2 + items.length * lineH;
        const canvasW = this.canvas.width / this.dpr;
        const canvasH = this.canvas.height / this.dpr;
        const x = canvasW - boxW - 12, y = canvasH - boxH - 12;

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
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 8]);

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
            ctx.lineWidth = 2;
        }

        this.root.links().forEach(link => {
            if (this.isNodeHidden(link.source) || this.isNodeHidden(link.target)) return;
            if (this._isRankHidden(link.target)) return;

            if (isDiff) {
                const status = link.target.data._diff_status || 'same';
                const color = diffColors[status] || diffColors.same;
                ctx.strokeStyle = status === 'same' ? 'rgba(0, 0, 0, 0.08)' : color;
                ctx.lineWidth = status === 'same' ? 2 : 4;
            }

            this._drawLink(ctx, link.source, link.target);
        });

        // Ghost edges: show original parent for "moved" nodes
        if (isDiff && tcOpts.diff_mode.show_ghost_edges) {
            // Build node position map for ghost edge lookup
            const nodeMap = new Map();
            this.root.each(n => nodeMap.set(String(n.id), n));

            ctx.save();
            ctx.setLineDash([8, 8]);
            ctx.strokeStyle = 'rgba(220, 53, 69, 0.3)';
            ctx.lineWidth = 2;

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

    drawNodes(ctx) {
        const searchIds = new Set(this.searchMatches.map(d => d.id));
        const watchNeighborIds = this._getWatchNeighborIds();

        this.root.each(node => {
            if (this.isNodeHidden(node)) return;

            const nid = String(node.id);
            const leaf = this.isLeafByRank(node);

            // Visible depth: skip hidden ranks
            if (this._isRankHidden(node)) return;

            const isSearch = searchIds.has(node.id);
            const isWatched = this.watchedNodes.has(nid);
            const isWatchNeighbor = watchNeighborIds.has(nid);

            let radius = 8 * this.textScale;
            if (isSearch) radius = 12 * this.textScale;

            // Watch node enlargement: 2x for watched, 1.5x for parent+children
            if (isWatched) {
                radius *= 2;
            } else if (isWatchNeighbor) {
                radius *= 1.5;
            }

            ctx.beginPath();
            ctx.arc(node.cx, node.cy, radius, 0, Math.PI * 2);
            ctx.fillStyle = isSearch ? '#ff6b35' : (node._color || '#6c757d');
            ctx.fill();

            if (isSearch) {
                ctx.strokeStyle = '#ff6b35';
                ctx.lineWidth = 4;
                ctx.stroke();
            }

            // Watch highlight ring (golden)
            if (isWatched) {
                ctx.strokeStyle = '#ffc107';
                ctx.lineWidth = 3;
                ctx.beginPath();
                ctx.arc(node.cx, node.cy, radius + 4, 0, Math.PI * 2);
                ctx.stroke();
            }

            // Hover highlight ring
            if (this.hoverNodeId && node.id === this.hoverNodeId) {
                ctx.beginPath();
                ctx.arc(node.cx, node.cy, radius + 10 * this.textScale, 0, Math.PI * 2);
                ctx.strokeStyle = '#00bcd4';
                ctx.lineWidth = 4;
                ctx.stroke();
            }

            // Collapsed indicator
            if (node._children) {
                ctx.beginPath();
                ctx.arc(node.cx, node.cy, radius + 6, 0, Math.PI * 2);
                ctx.strokeStyle = node._color || '#6c757d';
                ctx.lineWidth = 4;
                ctx.stroke();
                const s = radius + 2;
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 3;
                ctx.beginPath();
                ctx.moveTo(node.cx - s, node.cy);
                ctx.lineTo(node.cx + s, node.cy);
                ctx.moveTo(node.cx, node.cy - s);
                ctx.lineTo(node.cx, node.cy + s);
                ctx.stroke();
            }
            // Arc for internal nodes with value (count)
            else if (!leaf && node.value > 0) {
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

    // --- Canvas Labels (drawn in data space, scales with zoom) ---

    drawLabels(ctx) {
        if (!this.root || !this.viewDef) return;

        const labelKey = this.viewDef.hierarchy_options.label_key || 'name';
        const isRect = this.layoutMode === 'rectangular';

        const fontSize = Math.round(20 * this.textScale);
        const offset = Math.round(20 * this.textScale);
        ctx.textBaseline = 'middle';

        this.root.each(node => {
            if (this.isNodeHidden(node)) return;
            const label = node.data[labelKey] || '';
            if (!label) return;

            // Visible depth: skip hidden rank labels
            if (this._isRankHidden(node)) return;

            const nid = String(node.id);
            const isWatched = this.watchedNodes.has(nid);

            // Watched nodes get bold + larger font
            if (isWatched) {
                ctx.font = `bold ${Math.round(fontSize * 1.3)}px sans-serif`;
                ctx.fillStyle = '#856404';
            } else {
                ctx.font = `${fontSize}px sans-serif`;
                ctx.fillStyle = '#212529';
            }

            const nodeOffset = isWatched ? Math.round(offset * 1.5) : offset;

            if (isRect) {
                ctx.textAlign = 'left';
                ctx.fillText(label, node.cx + nodeOffset, node.cy);
            } else {
                // Radial: place label outside the node along the radial direction
                const angle = node.x || 0;
                const radAngle = (angle - 90) * Math.PI / 180; // radial outward direction
                ctx.save();
                // Always offset outward from center
                ctx.translate(node.cx + nodeOffset * Math.cos(radAngle),
                              node.cy + nodeOffset * Math.sin(radAngle));
                // Rotate text to be readable (right half: angle-90, left half: angle+90 to flip)
                if (angle > 0 && angle < 180) {
                    ctx.rotate((angle - 90) * Math.PI / 180);
                    ctx.textAlign = 'left';
                } else {
                    ctx.rotate((angle + 90) * Math.PI / 180);
                    ctx.textAlign = 'right';
                }
                ctx.fillText(label, 0, 0);
                ctx.restore();
            }
        });
    }

    /**
     * Draw labels during morph with fade for added/removed nodes.
     * Label angle/position is smoothly interpolated between base and compare.
     */
    _drawMorphLabels(ctx, fromPos, toPos, t) {
        if (!this.root || !this.viewDef) return;

        const labelKey = this.viewDef.hierarchy_options.label_key || 'name';
        const isRect = this.layoutMode === 'rectangular';
        const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

        const fontSize = Math.round(20 * this.textScale);
        const offset = Math.round(20 * this.textScale);
        ctx.fillStyle = '#212529';
        ctx.textBaseline = 'middle';
        ctx.font = `${fontSize}px sans-serif`;

        this.root.each(node => {
            if (this.isNodeHidden(node)) return;
            const label = node.data[labelKey] || '';
            if (!label) return;

            // Visible depth: skip hidden rank labels during morph
            if (this._isRankHidden(node)) return;

            // Compute opacity for added/removed
            let alpha = 1;
            const nid = String(node.id);
            const inBase = this._morphBasePositions && this._morphBasePositions.has(nid);
            const inComp = this._morphComparePositions && this._morphComparePositions.has(nid);
            if (inBase && !inComp) alpha = Math.max(0, 1 - t * 2);
            else if (!inBase && inComp) alpha = Math.max(0, (t - 0.5) * 2);
            if (alpha < 0.02) return;
            ctx.globalAlpha = alpha;

            if (isRect) {
                ctx.textAlign = 'left';
                ctx.fillText(label, node.cx + offset, node.cy);
            } else {
                // Interpolated angle (already set on node.x by renderMorphFrame)
                const angle = node.x || 0;
                const radAngle = (angle - 90) * Math.PI / 180;

                // Compute effective rotation that interpolates smoothly across the 180° flip.
                // Base and compare each have their own "label rotation":
                //   angle in (0,180): rotation = angle - 90   (text reads left-to-right)
                //   angle >= 180 or 0: rotation = angle + 90  (flipped to stay readable)
                const fp = fromPos.get(nid);
                const tp = toPos.get(nid);
                const fromAngle = fp ? fp.x : (tp ? tp.x : 0);
                const toAngle = tp ? tp.x : (fp ? fp.x : 0);

                const fromRot = (fromAngle > 0 && fromAngle < 180)
                    ? fromAngle - 90 : fromAngle + 90;
                const toRot = (toAngle > 0 && toAngle < 180)
                    ? toAngle - 90 : toAngle + 90;

                // Shortest-path angular interpolation for rotation
                let rotDiff = toRot - fromRot;
                if (rotDiff > 180) rotDiff -= 360;
                if (rotDiff < -180) rotDiff += 360;
                const rot = fromRot + rotDiff * ease;

                // Smoothly blend textAlign: compute a blend factor (0 = left, 1 = right)
                const fromAlign = (fromAngle > 0 && fromAngle < 180) ? 0 : 1;
                const toAlign = (toAngle > 0 && toAngle < 180) ? 0 : 1;
                const alignBlend = fromAlign + (toAlign - fromAlign) * ease;

                ctx.save();
                ctx.translate(node.cx + offset * Math.cos(radAngle),
                              node.cy + offset * Math.sin(radAngle));
                ctx.rotate(rot * Math.PI / 180);

                if (alignBlend < 0.5) {
                    ctx.textAlign = 'left';
                    ctx.fillText(label, 0, 0);
                } else {
                    ctx.textAlign = 'right';
                    ctx.fillText(label, 0, 0);
                }
                ctx.restore();
            }
        });
        ctx.globalAlpha = 1;
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
            right._zooming = true;
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
            left.render();
            right._zooming = false;
            right.render();
        });

    right.zoom
        .on('start', () => {
            if (syncing) return;
            right._zooming = true;
            left._zooming = true;
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
            right.render();
            left._zooming = false;
            left.render();
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

    // Sync radius scale
    left.onTextScaleSync = (val) => right.setTextScale(val);
    right.onTextScaleSync = (val) => left.setTextScale(val);

    // Sync visible depth
    left.onVisibleDepthSync = (depth) => right.setVisibleDepth(depth);
    right.onVisibleDepthSync = (depth) => left.setVisibleDepth(depth);

    // Sync hover highlight
    left.onHoverSync = (nodeId) => right.setHoverNode(nodeId);
    right.onHoverSync = (nodeId) => left.setHoverNode(nodeId);

    // Sync depth toggle

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
