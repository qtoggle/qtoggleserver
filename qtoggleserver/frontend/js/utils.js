/**
 * @namespace qtoggle.utils
 */

import * as Toast       from '$qui/messages/toast.js'
import * as ObjectUtils from '$qui/utils/object.js'

import * as NotificationsAPI from '$app/api/notifications.js'


/**
 * Help sorting items alphabetically and numerically at the same time, by adding zero padding to each number within the
 * given string.
 * @alias qtoggle.utils.alphaNumSortKey
 * @param {String} input the input string
 * @returns {String} the sort key
 */
export function alphaNumSortKey(input) {
    let re = new RegExp('\\d+')
    let l, m, s = input
    let n, key = ''
    while ((m = re.exec(s))) {
        l = m[0].length
        key += s.substring(0, m.index)
        s = s.substring(m.index + l)
        n = parseInt(m)
        key += ('0000000000' + n).slice(-10)
    }

    key += s

    return key
}

/**
 * Return all keys that correspond to different values in two objects or are present in only one of the two objects.
 * @alias qtoggle.utils.diffKeys
 * @param {Object} obj1
 * @param {Object} obj2
 * @returns {String[]} the list of distinct keys
 */
export function diffKeys(obj1, obj2) {
    let keys1 = Object.keys(obj1).filter(k => !(k in obj2))
    let keys2 = Object.keys(obj2).filter(k => !(k in obj1))
    let keys12 = Object.keys(obj1).filter(k => (k in obj2))

    return keys12.filter(k => obj1[k] !== obj2[k]).concat(keys1).concat(keys2)
}

/**
 * Transform an object name into a string suitable for an id.
 * @alias qtoggle.utils.nameToId
 * @param {String} name
 * @returns {String}
 */
export function nameToId(name) {
    return name.toLowerCase()
               .replace(new RegExp('[^a-z0-9]', 'g'), '-')
               .replace(new RegExp('(-+)', 'g'), '-')
}

/**
 * Create an IPv4 netmask from length.
 * @alias qtoggle.utils.netmaskFromLen
 * @param {Number} len
 * @returns {String} the netmask in "a.b.c.d" format
 */
export function netmaskFromLen(len) {
    let netmaskInt = 0
    let rem = 32 - len
    while (len > 0) {
        netmaskInt = (netmaskInt << 1) + 1
        len--
    }
    netmaskInt <<= rem

    return `${(netmaskInt >> 24) & 0xFF}.${(netmaskInt >> 16) & 0xFF}.${(netmaskInt >> 8) & 0xFF}.${netmaskInt & 0xFF}`
}

/**
 * Compute an IPv4 netmask length.
 * @alias qtoggle.utils.netmaskToLen
 * @param {String} netmask
 * @returns {Number} the length
 */
export function netmaskToLen(netmask) {
    let parts = netmask.split('.')
    let netmaskInt = (
        (parseInt(parts[0]) << 24) +
        (parseInt(parts[1]) << 16) +
        (parseInt(parts[2]) << 8) +
         parseInt(parts[3])
    )
    if (!netmaskInt) {
        return 0
    }

    let len = 0
    while ((netmaskInt & 0x01) === 0) {
        netmaskInt >>= 1
        len++
    }

    return 32 - len
}

/**
 * Resolve a JSON pointer (as defined by RFC6901) in a JSON object.
 * @alias qtoggle.utils.resolveJSONPointer
 * @param {Object} obj
 * @param {String} pointer
 * @returns {*} the resolved value
 */
export function resolveJSONPointer(obj, pointer) {
    let path
    if (pointer === '') {
        path = []
    }
    else if (pointer.charAt(0) !== '/') {
        throw new Error(`Invalid JSON pointer: ${pointer}`)
    }
    else {
        path = pointer.substring(1).split(/\//).map(s => s.replace(/~1/g, '/').replace(/~0/g, '~'))
    }

    path.forEach(function (p) {
        if (Array.isArray(obj)) {
            p = Number(p)
            if (isNaN(p) || p < 0 || p >= obj.length) {
                throw new Error(`JSON pointer reference not found: ${pointer}`)
            }

            obj = obj[p]
        }
        else if (ObjectUtils.isObject(obj)) {
            if (!(p in obj)) {
                throw new Error(`JSON pointer reference not found: ${pointer}`)
            }

            obj = obj[p]
        }
        else {
            throw new Error(`JSON pointer reference not found: ${pointer}`)
        }
    })

    return obj
}

function resolveJSONRefsRec(obj, rootObj) {
    if (Array.isArray(obj)) {
        obj.forEach(function (e, i) {
            obj[i] = resolveJSONRefsRec(e, rootObj)
        })
    }
    else if (ObjectUtils.isObject(obj)) {
        let keys = Object.keys(obj)
        if ((keys.length === 1) && (keys[0] === '$ref')) {
            let ref = obj['$ref'].substring(1)
            return resolveJSONPointer(rootObj, ref)
        }

        ObjectUtils.forEach(obj, function (key, value) {
            obj[key] = resolveJSONRefsRec(value, rootObj)
        })
    }

    return obj
}

/**
 * Recursively resolve all JSON pointer references (as defined by RFC6901) inside a JSON object.
 * @alias qtoggle.utils.resolveJSONRefs
 * @param {Object} obj
 * @returns {*} the resolved object
 */
export function resolveJSONRefs(obj) {
    return resolveJSONRefsRec(obj, obj)
}

function analyzeDecimationWindow(dataWindow, yField) {
    let minD = dataWindow[0]
    let maxD = dataWindow[0]
    for (let i = 0; i < dataWindow.length; i++) {
        let d = dataWindow[i]
        let y = d[yField]
        if (y < minD[yField]) {
            minD = d
        }
        else if (y > maxD[yField]) {
            maxD = d
        }
    }

    return {
        min: minD,
        max: maxD
    }
}

/**
 * Reduce the length of a list of data points, preserving local min/max values.
 * @alias qtoggle.common.decimate
 * @param {Object[]|Array[]} data
 * @param {Number} maxDataPointsLen
 * @param {Number|String} xField
 * @param {Number|String} yField
 * @returns {Object[]|Array[]}
 */
export function decimate(data, maxDataPointsLen, xField, yField) {
    if (data.length <= maxDataPointsLen) {
        return data
    }

    let windowSize = Math.ceil(data.length * 2 / maxDataPointsLen)
    let decimatedData = []
    for (let i = 0; i < maxDataPointsLen / 2; i++) {
        let win = data.slice(i * windowSize, (i + 1) * windowSize)
        if (!win.length) {
            break
        }
        let analysis = analyzeDecimationWindow(win, yField)
        if (analysis.min[xField] < analysis.max[xField]) {
            decimatedData.push(analysis.min, analysis.max)
        }
        else {
            decimatedData.push(analysis.max, analysis.min)
        }
    }

    /* Eliminate duplicates that may occur (on x axis) */
    for (let i = 1; i < decimatedData.length; i++) {
        if (decimatedData[i - 1][xField] === decimatedData[i][xField]) {
            decimatedData.splice(i, 1)
            i--
        }
    }

    return decimatedData
}

/**
 * Apply moving average filter to a list of data points.
 * @alias qtoggle.common.movingAverage
 * @param {Object[]|Array[]} data
 * @param {Number} length
 * @param {Number|String} xField
 * @param {Number|String} yField
 * @returns {Object[]|Array[]}
 */
export function movingAverage(data, length, xField, yField) {
    let filteredHistory = []
    let lengthHalf = Math.floor(length / 2)
    let sampleIsObject = ObjectUtils.isObject(data[0])
    for (let i = 0; i < data.length; i++) {
        let wStart = Math.max(0, i - lengthHalf)
        let wStop = Math.min(data.length, i - lengthHalf + length)
        let wData = data.slice(wStart, wStop)
        let sample = data[i]
        let filteredValue = wData.reduce((a, b) => a + b[yField], 0) / wData.length

        let filteredSample
        if (sampleIsObject) {
            filteredSample = {[yField]: filteredValue, [xField]: sample[xField]}
        }
        else { /* Assuming samples are arrays */
            filteredSample = []
            filteredSample[xField] = sample[xField]
            filteredSample[yField] = filteredValue
        }

        filteredHistory.push(filteredSample)
    }

    return filteredHistory
}

/**
 * Show a toast error message according to the given error object.
 * @param {Error} error the error to show as toast message
 */
export function showToastError(error) {
    /* Don't show a toast message if disconnected, since the user already sees the "connecting..." dialog */
    if (NotificationsAPI.isConnected()) {
        Toast.error(error.message)
    }
}
