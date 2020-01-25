/**
 * @namespace qtoggle.common
 */

import StickyModalProgressMessage from '$qui/messages/sticky-modal-progress-message.js'
import * as ObjectUtils           from '$qui/utils/object.js'


/**
 * Number of seconds within which a device should gracefully go offline.
 * @alias qtoggle.common.GO_OFFLINE_TIMEOUT
 * @type {Number}
 */
export const GO_OFFLINE_TIMEOUT = 20

/**
 * Number of seconds within which a device should come back online.
 * @alias qtoggle.common.COME_ONLINE_TIMEOUT
 * @type {Number}
 */
export const COME_ONLINE_TIMEOUT = 60 /* Seconds */

let globalProgressMessage = null


/**
 * Return the singleton instance of the global progress message.
 * @alias qtoggle.common.getGlobalProgressMessage
 * @returns {qui.messages.StickyModalProgressMessage}
 */
export function getGlobalProgressMessage() {
    if (globalProgressMessage == null) {
        globalProgressMessage = new StickyModalProgressMessage({progressOptions: {caption: ''}})
    }

    return globalProgressMessage
}

/**
 * Combine two sets of attribute definitions.
 * @alias qtoggle.common.combineAttrdefs
 * @param {Object} defs1
 * @param {Object} defs2
 * @returns {Object}
 */
export function combineAttrdefs(defs1, defs2) {
    let combined = ObjectUtils.copy(defs1, /* deep = */ true)

    ObjectUtils.forEach(defs2, function (name, def) {
        combined[name] = ObjectUtils.combine(combined[name] || {}, def)
    })

    return combined
}

/**
 * Prepare device attributes to be displayed on device form.
 * @alias qtoggle.common.preprocessDeviceAttrs
 * @param {Object} attrs device attributes
 * @returns {Object} prepared device attributes
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
