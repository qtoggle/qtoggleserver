
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
