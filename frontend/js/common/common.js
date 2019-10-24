
import StickyModalProgressMessage                from '$qui/messages/sticky-modal-progress-message.js'
import * as ObjectUtils                          from '$qui/utils/object.js'


export const GO_OFFLINE_TIMEOUT = 20 /* Seconds */
export const COME_ONLINE_TIMEOUT = 60 /* Seconds */

let globalProgressMessage = null


export function getGlobalProgressMessage() {
    if (globalProgressMessage == null) {
        globalProgressMessage = new StickyModalProgressMessage({progressOptions: {caption: ''}})
    }

    return globalProgressMessage
}

export function combineAttrdefs(defs1, defs2) {
    let combined = ObjectUtils.copy(defs1, /* deep = */ true)

    ObjectUtils.forEach(defs2, function (name, def) {
        combined[name] = ObjectUtils.combine(combined[name] || {}, def)
    })

    return combined
}

/**
 * @param {Object} attrs
 * @returns {Object}
 */
export function preprocessDeviceAttrs(attrs) {
    let processedAttrs = ObjectUtils.copy(attrs, /* deep = */ true)

    /* Special password handling */
    processedAttrs = ObjectUtils.mapValue(processedAttrs, function (value, key) {
        if (key.endsWith('_password')) {
            if (value) {
                return '*****'
            }
        }

        return value
    })

    return processedAttrs
}
