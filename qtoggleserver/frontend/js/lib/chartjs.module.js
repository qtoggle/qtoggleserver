
import * as ChartJS from '$node/chart.js/dist/chart.esm.js'

window['chart.js'] = ChartJS

export * from '$node/chart.js/dist/chart.esm.js'

/* Hack to allow plugins such as zoom to access Chart.js helpers.
 * This needs to be manually updated each time we upgrade chart.js version.
 * The first part of exports is separately added as it is not found among the imports in chart.esm.js. */

export {
    ar as clone,

    r as requestAnimFrame, a as resolve, e as effects, c as color, i as isObject, d as defaults, n as noop,
    v as valueOrDefault, u as unlistenArrayEvents, l as listenArrayEvents, m as merge, b as isArray,
    f as resolveObjectKey, g as getHoverColor, _ as _capitalize, h as mergeIf, s as sign, j as _merger,
    k as isNullOrUndef, o as clipArea, p as unclipArea, q as _arrayUnique, t as toRadians, T as TAU, H as HALF_PI,
    P as PI, w as isNumber, x as _limitValue, y as _lookupByKey, z as getRelativePosition$1, A as _isPointInArea,
    B as _rlookupByKey, C as toPadding, D as each, E as getMaximumSize, F as _getParentNode, G as readUsedSize,
    I as throttled, J as supportsEventListenerOptions, K as log10, L as finiteOrDefault, M as isNumberFinite,
    N as callback, O as toDegrees, Q as _measureText, R as _int16Range, S as _alignPixel, U as toFont, V as _factorize,
    W as uid, X as retinaScale, Y as clear, Z as _elementsEqual, $ as getAngleFromPoint, a0 as _angleBetween,
    a1 as _updateBezierControlPoints, a2 as _computeSegments, a3 as _boundSegments, a4 as _steppedInterpolation,
    a5 as _bezierInterpolation, a6 as _pointInLine, a7 as _steppedLineTo, a8 as _bezierCurveTo, a9 as drawPoint,
    aa as toTRBL, ab as toTRBLCorners, ac as _normalizeAngle, ad as _boundSegment, ae as INFINITY, af as getRtlAdapter,
    ag as overrideTextDirection, ah as restoreTextDirection, ai as distanceBetweenPoints, aj as _setMinAndMaxByKey,
    ak as _decimalPlaces, al as almostEquals, am as almostWhole, an as _longestText, ao as _filterBetween, ap as _lookup
} from '$node/chart.js/dist/chunks/helpers.segment.js'
