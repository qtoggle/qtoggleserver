
import * as ObjectUtils from '$qui/utils/object.js'


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


/**
 * Helps sorting items alphabetically and numerically at the same time,
 * by adding zero padding to each number within the given string.
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
 * Returns all keys that correspond to different values in two objects or are present in only one of them.
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

export function nameToId(name) {
    return name.toLowerCase()
               .replace(new RegExp('[^a-z0-9]', 'g'), '-')
               .replace(new RegExp('(-+)', 'g'), '-')
}

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

export function resolveJSONRefs(obj) {
    return resolveJSONRefsRec(obj, obj)
}
