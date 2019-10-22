import {gettext}                  from '$qui/base/i18n.js'
import {Mixin}                    from '$qui/base/mixwith.js'
import {
    CheckField, ComboField, LabelsField, NumericField, PasswordField, SliderField, TextField, UpDownField
}                                 from '$qui/forms/common-fields.js'
import {ValidationError}          from '$qui/forms/forms.js'
import StickyModalProgressMessage from '$qui/messages/sticky-modal-progress-message.js'
import * as ArrayUtils            from '$qui/utils/array.js'
import * as HTML                  from '$qui/utils/html.js'
import * as ObjectUtils           from '$qui/utils/object.js'
import * as StringUtils           from '$qui/utils/string.js'


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
