/**
 * @namespace qtoggle.api.attrdeffields
 */

import {gettext}        from '$qui/base/i18n.js'
import {CompositeField} from '$qui/forms/common-fields/common-fields.js'
import {ComboField}     from '$qui/forms/common-fields/common-fields.js'
import {LabelsField}    from '$qui/forms/common-fields/common-fields.js'
import {TextField}      from '$qui/forms/common-fields/common-fields.js'
import * as Theme       from '$qui/theme.js'

import * as Cache       from '$app/cache.js'


/**
 * @alias qtoggle.api.attrdeffields.WiFiSignalStrengthField
 * @extends qui.forms.commonfields.ProgressDiskField
 */
export class WiFiSignalStrengthField extends LabelsField {

    static BACKGROUNDS = {
        0: '@red-color',
        1: '@orange-color',
        2: '@yellow-color',
        3: '@green-color'
    }

    static LABELS = {
        0: gettext('weak'),
        1: gettext('fair'),
        2: gettext('good'),
        3: gettext('excellent')
    }


    valueToWidget(value) {
        value = Math.min(3, Math.max(0, value))

        let background = Theme.getColor(this.constructor.BACKGROUNDS[value])
        let label = this.constructor.LABELS[value]
        let text = `${label} (${value}/3)`

        super.valueToWidget([{text, background}])
    }

}

/**
 * @alias qtoggle.api.attrdeffields.WiFiSignalStrengthField
 * @extends qui.forms.commonfields.ProgressDiskField
 */
export class ConfigNameField extends CompositeField {

    /**
     * @constructs
     * @param {Object} attrs
     * @param {...*} args parent class parameters
     */
    constructor({attrs, ...args} = {}) {
        let vendor = attrs['vendor'] || ''
        let choices = []
        if (vendor.startsWith('qtoggle/')) {
            /* Build choices from provisioning configs for devices running official qToggle firmware */
            let deviceFamily = vendor.substring(8)
            choices = Cache.getProvisioningConfigs()
            choices = choices.filter(c => c.display_name != null)
            choices = choices.filter(c => c.name.startsWith(`${deviceFamily}/`))
            choices = choices.map(function (config) {
                return {
                    label: config.display_name,
                    value: config.name.substring(deviceFamily.length + 1)
                }
            })
        }

        choices.push({label: gettext('custom') + '...', value: 'custom'})

        super({
            fields: [
                new ComboField({
                    name: 'combo',
                    choices: choices,
                    filterEnabled: true,

                    onChange(value, form) {
                        that.updateCustomFieldVisibility()
                    }

                }),
                new TextField({
                    name: 'custom',
                    placeholder: gettext('custom configuration...')
                })
            ],
            flow: 'vertical',
            ...args
        })

        let that = this

        this._choices = choices
    }

    setValue(value) {
        super.setValue(value)

        this.updateCustomFieldVisibility()
    }

    valueToWidget(value) {
        let existingValue = this._choices.find(c => c.value === value) != null

        super.valueToWidget({
            combo: existingValue ? value : 'custom',
            custom: value
        })
    }

    widgetToValue() {
        let compositeValue = super.widgetToValue()
        if (compositeValue.combo === 'custom') {
            return compositeValue.custom
        }
        else {
            return compositeValue.combo
        }
    }

    updateCustomFieldVisibility() {
        let comboField = this.getField('combo')
        let customField = this.getField('custom')

        if (comboField.getValue() === 'custom') {
            customField.show()
        }
        else {
            customField.hide()
        }
    }

}
