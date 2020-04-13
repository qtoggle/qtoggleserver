/**
 * @namespace qtoggle.utils
 */

import * as ObjectUtils from '$qui/utils/object.js'


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


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
    let netmaskInt = (parseInt(parts[0]) << 24) + (parseInt(parts[1]) << 16) + (parseInt(parts[2]) << 8) + parseInt(parts[3])
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
