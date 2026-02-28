/**
 * SCODA Desktop — Radial Hierarchy View
 * D3-based radial tree visualization for hierarchy data.
 * Lazy-loads D3.js only when this view is activated.
 */

// D3 lazy load state
let d3Ready = null;

// Radial view state
let radialRoot = null;
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
    const wrap = document.getElementById('radial-canvas-wrap');
    wrap.innerHTML = '<div class="loading">Loading D3.js...</div>';

    try {
        await ensureD3Loaded();
    } catch (e) {
        wrap.innerHTML = '<div class="text-danger">Failed to load D3.js. Check your internet connection.</div>';
        return;
    }

    // Restore canvas + SVG structure
    wrap.innerHTML = '<canvas id="radial-canvas"></canvas><svg id="radial-labels"></svg>';

    const view = manifest.views[viewKey];
    if (!view) return;

    radialViewDef = view;
    radialViewKey = viewKey;
    radialDepthHidden = false;
    radialSearchMatches = [];
    radialFocusNode = null;

    // Setup canvas
    radialCanvas = document.getElementById('radial-canvas');
    radialCtx = radialCanvas.getContext('2d');
    radialLabelsSvg = d3.select('#radial-labels');
    radialDpr = window.devicePixelRatio || 1;

    resizeRadialCanvas();

    // Build toolbar
    buildRadialToolbar(view);

    // Fetch data and build hierarchy
    try {
        radialRoot = await buildRadialHierarchy(view);
    } catch (e) {
        wrap.innerHTML = `<div class="text-danger">Error loading data: ${e.message}</div>`;
        return;
    }

    if (!radialRoot) {
        wrap.innerHTML = '<div class="text-muted" style="padding:20px;text-align:center;">No hierarchy data found.</div>';
        return;
    }

    // Compute layout
    computeRadialLayout(radialRoot, view);

    // Assign colors
    assignRadialColors(radialRoot, view);

    // Build quadtree for hover
    buildRadialQuadtree(radialRoot);

    // Setup zoom
    setupRadialZoom();

    // Initial render
    radialTransform = d3.zoomIdentity;
    renderRadial();
    updateRadialBreadcrumb();
}

// --- Data Loading ---

async function buildRadialHierarchy(view) {
    const hOpts = view.hierarchy_options;
    const rOpts = view.radial_display || {};
    const rows = await fetchQuery(view.source_query);

    if (!rows || rows.length === 0) return null;

    // If edge_query is specified, load edges separately
    if (rOpts.edge_query) {
        const edges = await fetchQuery(rOpts.edge_query);
        const parentMap = new Map(edges.map(e => [e.child_id, e.parent_id]));
        rows.forEach(n => {
            n[hOpts.parent_key] = parentMap.get(n[hOpts.id_key]) || null;
        });
    }

    const root = d3.stratify()
        .id(d => d[hOpts.id_key])
        .parentId(d => d[hOpts.parent_key])
        (rows);

    // Sum counts
    const countKey = rOpts.count_key || hOpts.count_key;
    if (countKey) {
        root.sum(d => d[countKey] || 0);
    } else {
        root.count();
    }

    // Sort by label for consistent layout
    const labelKey = hOpts.label_key || 'name';
    root.sort((a, b) => (a.data[labelKey] || '').localeCompare(b.data[labelKey] || ''));

    return root;
}

// --- Layout ---

function computeRadialLayout(root, view) {
    const rOpts = view.radial_display || {};
    radialOuterRadius = Math.min(radialWidth, radialHeight) * 0.42;

    d3.cluster().size([360, radialOuterRadius])(root);

    // Override radii by rank if specified
    const rankRadius = rOpts.rank_radius;
    const rankKey = view.hierarchy_options.rank_key || 'rank';
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

// --- Colors ---

function assignRadialColors(root, view) {
    const rOpts = view.radial_display || {};
    const colorKey = rOpts.color_key;
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
    const toolbar = document.getElementById('radial-toolbar');
    const rOpts = view.radial_display || {};
    let html = '';

    // Search
    html += '<input type="text" id="radial-search" placeholder="Search nodes..." autocomplete="off">';

    // Depth toggle
    if (rOpts.depth_toggle && rOpts.leaf_rank) {
        html += `<button id="radial-depth-btn" title="Toggle leaf nodes">
                    <i class="bi bi-layers"></i> ${rOpts.leaf_rank}
                 </button>`;
    }

    // Reset zoom
    html += '<button id="radial-reset-btn" title="Reset zoom"><i class="bi bi-arrows-fullscreen"></i></button>';

    toolbar.innerHTML = html;

    // Event: search
    const searchInput = document.getElementById('radial-search');
    if (searchInput) {
        let timer;
        searchInput.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(() => radialSearch(searchInput.value.trim()), 200);
        });
    }

    // Event: depth toggle
    const depthBtn = document.getElementById('radial-depth-btn');
    if (depthBtn) {
        depthBtn.addEventListener('click', () => {
            radialDepthHidden = !radialDepthHidden;
            depthBtn.classList.toggle('active', radialDepthHidden);
            renderRadial();
        });
    }

    // Event: reset
    const resetBtn = document.getElementById('radial-reset-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            radialFocusNode = null;
            const svg = d3.select('#radial-canvas-wrap');
            svg.transition().duration(500).call(radialZoom.transform, d3.zoomIdentity);
            updateRadialBreadcrumb();
        });
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
        .on('dblclick.zoom', null)  // disable default double-click zoom
        .on('mousemove', onRadialMouseMove)
        .on('click', onRadialClick)
        .on('dblclick', onRadialDblClick);
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

    const tooltip = document.getElementById('radial-tooltip');
    if (nearest && !isNodeHidden(nearest)) {
        const labelKey = radialViewDef.hierarchy_options.label_key || 'name';
        const rankKey = radialViewDef.hierarchy_options.rank_key || 'rank';
        const rOpts = radialViewDef.radial_display || {};
        const countKey = rOpts.count_key || radialViewDef.hierarchy_options.count_key;

        let html = `<div class="rt-name">${nearest.data[labelKey] || nearest.id}</div>`;
        if (nearest.data[rankKey]) {
            html += `<div class="rt-rank">${nearest.data[rankKey]}</div>`;
        }
        if (countKey && nearest.value !== undefined) {
            html += `<div class="rt-count">${countKey}: ${nearest.value}</div>`;
        }

        tooltip.innerHTML = html;
        tooltip.style.display = '';
        tooltip.style.left = (mx + 12) + 'px';
        tooltip.style.top = (my - 10) + 'px';

        // Keep tooltip inside viewport
        const rect = tooltip.getBoundingClientRect();
        const wrap = document.getElementById('radial-canvas-wrap').getBoundingClientRect();
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

    const rOpts = radialViewDef.radial_display || {};

    // Detail modal integration
    if (rOpts.on_node_click && nearest.data[rOpts.on_node_click.id_field]) {
        const detailView = rOpts.on_node_click.detail_view;
        if (detailView && typeof openDetailModal === 'function') {
            openDetailModal(detailView, nearest.data[rOpts.on_node_click.id_field]);
            return;
        }
    }

    // If internal node, zoom into subtree
    if (nearest.children && nearest.children.length > 0) {
        radialFocusNode = nearest;
        zoomToNode(nearest, Math.min(radialTransform.k * 2, 15));
        updateRadialBreadcrumb();
    }
}

function onRadialDblClick(event) {
    event.preventDefault();
    if (radialFocusNode && radialFocusNode.parent) {
        radialFocusNode = radialFocusNode.parent === radialRoot ? null : radialFocusNode.parent;
        if (radialFocusNode) {
            zoomToNode(radialFocusNode, Math.max(radialTransform.k / 2, 0.5));
        } else {
            d3.select(radialCanvas)
                .transition().duration(500)
                .call(radialZoom.transform, d3.zoomIdentity);
        }
        updateRadialBreadcrumb();
    }
}

// --- Breadcrumb ---

function updateRadialBreadcrumb() {
    const bc = document.getElementById('radial-breadcrumb');
    if (!bc) return;

    if (!radialFocusNode) {
        bc.innerHTML = '';
        return;
    }

    const labelKey = radialViewDef.hierarchy_options.label_key || 'name';
    const path = radialFocusNode.ancestors().reverse();
    const parts = path.map((node, i) => {
        const label = node.data[labelKey] || node.id || 'Root';
        const isCurrent = i === path.length - 1;
        return `<span class="${isCurrent ? 'current' : ''}" onclick="radialBcClick('${node.id}')">${label}</span>`;
    });
    bc.innerHTML = parts.join('<span class="bc-sep">/</span>');
}

function radialBcClick(nodeId) {
    if (!radialRoot) return;
    let target = null;
    radialRoot.each(d => { if (d.id === nodeId) target = d; });
    if (target) {
        radialFocusNode = target === radialRoot ? null : target;
        if (radialFocusNode) {
            zoomToNode(radialFocusNode, 3);
        } else {
            d3.select(radialCanvas)
                .transition().duration(500)
                .call(radialZoom.transform, d3.zoomIdentity);
        }
        updateRadialBreadcrumb();
    }
}

// --- Rendering ---

function resizeRadialCanvas() {
    const wrap = document.getElementById('radial-canvas-wrap');
    radialWidth = wrap.clientWidth;
    radialHeight = wrap.clientHeight;

    radialCanvas = document.getElementById('radial-canvas');
    radialCanvas.width = radialWidth * radialDpr;
    radialCanvas.height = radialHeight * radialDpr;
    radialCanvas.style.width = radialWidth + 'px';
    radialCanvas.style.height = radialHeight + 'px';

    radialCtx = radialCanvas.getContext('2d');
    radialCtx.setTransform(radialDpr, 0, 0, radialDpr, 0, 0);
}

function isNodeHidden(node) {
    if (!radialDepthHidden) return false;
    const rOpts = radialViewDef.radial_display || {};
    const leafRank = rOpts.leaf_rank;
    const rankKey = radialViewDef.hierarchy_options.rank_key || 'rank';
    return leafRank && node.data[rankKey] === leafRank;
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

    // Draw guide circles (concentric rings per depth)
    drawGuideCircles(ctx);

    // Draw links
    drawLinks(ctx);

    // Draw nodes
    drawNodes(ctx, t.k);

    ctx.restore();

    // Update SVG labels (LOD)
    updateRadialLabels(t);
}

function drawGuideCircles(ctx) {
    if (!radialRoot) return;

    // Collect unique depths
    const depths = new Set();
    radialRoot.each(d => {
        if (!isNodeHidden(d)) depths.add(d.y);
    });

    ctx.strokeStyle = 'rgba(0, 0, 0, 0.06)';
    ctx.lineWidth = 0.5;
    ctx.setLineDash([4, 4]);

    for (const r of depths) {
        if (r === 0) continue;
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.stroke();
    }

    ctx.setLineDash([]);
}

function drawLinks(ctx) {
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.lineWidth = 0.8;

    radialRoot.links().forEach(link => {
        if (isNodeHidden(link.source) || isNodeHidden(link.target)) return;

        ctx.beginPath();
        ctx.moveTo(link.source.cx, link.source.cy);

        // Curved link: radial step
        const midAngle = (link.source.x + link.target.x) / 2;
        const midR = (link.source.y + link.target.y) / 2;
        const midA = (midAngle - 90) * Math.PI / 180;
        const midX = midR * Math.cos(midA);
        const midY = midR * Math.sin(midA);

        ctx.quadraticCurveTo(midX, midY, link.target.cx, link.target.cy);
        ctx.stroke();
    });
}

function drawNodes(ctx, k) {
    const searchIds = new Set(radialSearchMatches.map(d => d.id));

    radialRoot.each(node => {
        if (isNodeHidden(node)) return;

        const isLeaf = !node.children || node.children.length === 0;
        const isSearch = searchIds.has(node.id);

        // Node size: bigger for higher rank nodes
        let radius = isLeaf ? 2 : Math.max(3, 6 - node.depth);
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

        // Arc for internal nodes with value (count)
        if (!isLeaf && node.value > 0 && k > 1) {
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
    const maxLabels = 150;

    // Viewport bounds in data coordinates
    const vpLeft = (-t.x - cx * t.k) / t.k;
    const vpTop = (-t.y - cy * t.k) / t.k;
    const vpRight = vpLeft + radialWidth / t.k;
    const vpBottom = vpTop + radialHeight / t.k;

    radialRoot.each(node => {
        if (isNodeHidden(node)) return;

        const isLeaf = !node.children || node.children.length === 0;
        const depth = node.depth;

        let show = false;

        if (depth === 0) {
            show = true; // always show root
        } else if (depth === 1) {
            show = k >= 0.5; // top-level children
        } else if (k < 1.5) {
            show = depth <= 1;
        } else if (k < 3) {
            show = depth <= 2;
        } else if (k < 6) {
            show = !isLeaf || depth <= 3;
        } else {
            // High zoom: show if in viewport
            if (node.cx >= vpLeft && node.cx <= vpRight &&
                node.cy >= vpTop && node.cy <= vpBottom) {
                show = true;
            }
        }

        if (show) labelsToShow.push(node);
    });

    // Limit labels
    const limited = labelsToShow.slice(0, maxLabels);

    // Update SVG
    const sel = radialLabelsSvg.selectAll('text')
        .data(limited, d => d.id);

    sel.exit().remove();

    const enter = sel.enter().append('text')
        .attr('font-size', d => {
            if (d.depth === 0) return '11px';
            if (d.depth === 1) return '10px';
            return '9px';
        })
        .attr('fill', '#212529')
        .attr('text-anchor', d => {
            const angle = d.x || 0;
            return (angle > 0 && angle < 180) ? 'start' : 'end';
        })
        .attr('dominant-baseline', 'central');

    const merged = enter.merge(sel);

    merged
        .attr('transform', d => {
            const sx = t.x + (d.cx + cx) * t.k;
            const sy = t.y + (d.cy + cy) * t.k;
            const angle = d.x || 0;
            // Offset label slightly from node
            const offset = 8;
            const labelAngle = (angle - 90) * Math.PI / 180;
            const lx = sx + offset * Math.cos(labelAngle) * (angle > 0 && angle < 180 ? 1 : -1);
            const ly = sy + offset * Math.sin(labelAngle) * (angle > 0 && angle < 180 ? 1 : -1);
            // Rotate text to follow radial direction
            let rotation = angle > 180 ? angle - 270 : angle - 90;
            return `translate(${sx + offset * (angle > 0 && angle < 180 ? 1 : -1)}, ${sy}) rotate(${rotation})`;
        })
        .attr('text-anchor', d => {
            const angle = d.x || 0;
            return (angle > 0 && angle < 180) ? 'start' : 'end';
        })
        .attr('font-size', d => {
            const base = d.depth === 0 ? 11 : d.depth === 1 ? 10 : 9;
            // Scale font slightly with zoom but keep readable
            return Math.min(base, Math.max(7, base / Math.sqrt(k))) + 'px';
        })
        .attr('opacity', d => {
            if (d.depth === 0) return 1;
            if (d.depth === 1) return Math.min(1, k * 0.8);
            return Math.min(1, (k - 1) * 0.5);
        })
        .text(d => {
            const label = d.data[labelKey] || d.id || '';
            // Truncate long labels
            const maxLen = d.depth <= 1 ? 30 : 20;
            return label.length > maxLen ? label.substring(0, maxLen) + '...' : label;
        });
}

// --- Resize Handling ---

let radialResizeTimer = null;
window.addEventListener('resize', () => {
    if (!radialViewDef) return;
    clearTimeout(radialResizeTimer);
    radialResizeTimer = setTimeout(() => {
        const radialContainer = document.getElementById('view-radial');
        if (radialContainer && radialContainer.style.display !== 'none') {
            resizeRadialCanvas();
            if (radialRoot) {
                computeRadialLayout(radialRoot, radialViewDef);
                buildRadialQuadtree(radialRoot);
                renderRadial();
            }
        }
    }, 200);
});
