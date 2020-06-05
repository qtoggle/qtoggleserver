
import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields/common-fields.js'
import {ColorComboField} from '$qui/forms/common-fields/common-fields.js'
import {NumericField}    from '$qui/forms/common-fields/common-fields.js'
import {UpDownField}     from '$qui/forms/common-fields/common-fields.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as ArrayUtils   from '$qui/utils/array.js'

import PortPickerField  from '$app/dashboard/widgets/port-picker-field.js'
import * as Widgets     from '$app/dashboard/widgets/widgets.js'
import WidgetConfigForm from '$app/dashboard/widgets/widget-config-form.js'

import PushButton from './push-button.js'


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


class ConfigForm extends WidgetConfigForm {

    constructor({...args}) {
        super({
            fields: [
                new ColorComboField({
                    name: 'color',
                    label: gettext('Color'),
                    filterEnabled: true,
                    required: true
                }),
                new PortPickerField({
                    name: 'portId',
                    label: gettext('Port'),
                    required: true,
                    onChange: (value, form) => form._updateSeqFields()
                }),
                new CheckField({
                    name: 'repeat',
                    label: gettext('Repeat'),
                    separator: true,
                    onChange: (value, form) => form._updateRepeatFields()
                }),
                new CheckField({
                    name: 'repeatForever',
                    label: gettext('Repeat Forever'),
                    onChange: (value, form) => form._updateRepeatFields()
                }),
                new NumericField({
                    name: 'repeatCount',
                    label: gettext('Repeat Count'),
                    unit: gettext('times'),
                    required: true,
                    min: 2,
                    max: 65535
                }),
                new UpDownField({
                    name: 'seqLength',
                    label: gettext('Sequence Length'),
                    separator: true,
                    min: 0,
                    max: 100,
                    onChange: (value, form) => form._updateSeqFields()
                })
            ],
            ...args
        })
    }

    onUpdateFromWidget() {
        this._updateSeqFields()
        this._updateRepeatFields()
    }

    _updateSeqFields() {
        let seqValueFields = this.getFields().filter(field => field.getName().match(new RegExp('seqValue\\d+')))
        let seqDelayFields = this.getFields().filter(field => field.getName().match(new RegExp('seqDelay\\d+')))
        let seqFields = seqDelayFields.concat(seqValueFields)

        let lastSeqFieldNo = seqDelayFields.length - 1

        let data = this.getUnvalidatedData()
        let port = this.getPort(data.portId)

        let isBoolean = !(port && port.type === 'number')
        let field = this.getField('seqValue0')
        let hasBooleanFields = field ? field instanceof CheckField : false

        if (isBoolean !== hasBooleanFields) {
            /* Value type differs, we must recreate all fields */
            seqFields.forEach(function (field) {
                this.removeField(field)
            }, this)

            lastSeqFieldNo = -1
        }

        /* Add new needed fields */
        ArrayUtils.range(lastSeqFieldNo + 1, data.seqLength).forEach(function (no) {

            let fields = this._addSeqFields(no, port)

            seqFields.push(fields.valueField)
            seqFields.push(fields.delayField)

        }, this)

        /* Show all used fields */
        ArrayUtils.range(0, data.seqLength).forEach(function (no) {

            let fields = this._getSeqFields(no)

            fields.valueField.show()
            fields.delayField.show()

        }, this)

        /* Hide all unused fields */
        ArrayUtils.range(data.seqLength, lastSeqFieldNo + 1).forEach(function (no) {

            let fields = this._getSeqFields(no)

            fields.valueField.hide()
            fields.delayField.hide()

        }, this)
    }

    _addSeqFields(no, port) {
        let isBoolean = !(port && port.type === 'number')

        let min = null
        let max = null
        let integer = false
        let step = null
        if (port) {
            min = port.min
            max = port.max
            integer = port.integer
            step = port.step
        }

        let valueField
        if (isBoolean) {
            valueField = new CheckField({
                name: `seqValue${no}`,
                label: `${gettext('Value')} ${no + 1}`,
                required: false,
                separator: true
            })
        }
        else {
            valueField = new NumericField({
                name: `seqValue${no}`,
                label: `${gettext('Value')} ${no + 1}`,
                min: min, // TODO do these options work?
                max: max,
                integer: integer,
                step: step,
                required: true,
                separator: true
            })
        }

        this.addField(-1, valueField)

        let delayField = new NumericField({
            name: `seqDelay${no}`,
            label: `${gettext('Delay')} ${no + 1}`,
            required: true,
            unit: 'ms',
            min: 1, // TODO do these options work?
            max: 60000
        })

        this.addField(-1, delayField)

        return {
            valueField: valueField,
            delayField: delayField
        }
    }

    _getSeqFields(no) {
        let valueField = this.getField(`seqValue${no}`)
        let delayField = this.getField(`seqDelay${no}`)

        return {
            valueField: valueField,
            delayField: delayField
        }
    }

    _updateRepeatFields() {
        let data = this.getUnvalidatedData()
        let repeatForeverField = this.getField('repeatForever')
        let repeatCountField = this.getField('repeatCount')

        if (data.repeat) {
            repeatForeverField.show()
            if (data.repeatForever) {
                repeatCountField.hide()
            }
            else {
                repeatCountField.show()
                if (data.repeatCount < 2) {
                    data.repeatCount = 2
                    this.setData({repeatCount: 2})
                }
            }
        }
        else {
            repeatForeverField.hide()
            repeatCountField.hide()
        }
    }

    fromWidget(widget) {
        let data = super.fromWidget(widget)

        data.seqLength = data.delays.length
        ArrayUtils.range(0, data.seqLength).forEach(function (no) {
            data[`seqValue${no}`] = data.values[no]
            data[`seqDelay${no}`] = data.delays[no]
        })

        if (data.repeatCount >= 2) {
            data.repeat = true
            data.repeatForever = false
        }
        else if (data.repeatCount === 1) {
            data.repeat = false
            data.repeatForever = false
        }
        else { /* Assuming 0 */
            data.repeat = true
            data.repeatForever = true
        }

        return data
    }

    toWidget(data, widget) {
        data.values = []
        data.delays = []

        ArrayUtils.range(0, data.seqLength).forEach(function (no) {
            data.values[no] = data[`seqValue${no}`]
            data.delays[no] = data[`seqDelay${no}`]
        })

        if (data.repeat) {
            if (data.repeatForever) {
                data.repeatCount = 0
            }
        }
        else {
            data.repeatCount = 1
        }

        super.toWidget(data, widget)
    }

}


/**
 * @alias qtoggle.dashboard.widgets.pushbuttons.SequencePushButton
 * @extends qtoggle.dashboard.widgets.Widget
 */
class SequencePushButton extends PushButton {

    /**
     * @constructs
     */
    constructor() {
        super()

        this._values = []
        this._delays = []
        this._repeatCount = 1
    }

    handlePress() {
        this.setPortSequence(this._portId, this._values, this._delays, this._repeatCount)
    }

    handleRelease() {
    }

    configToJSON() {
        return {
            color: this._color,
            portId: this._portId,
            values: this._values.slice(),
            delays: this._delays.slice(),
            repeatCount: this._repeatCount
        }
    }

    configFromJSON(json) {
        if (json.color) {
            this._color = json.color
        }
        if (json.portId) {
            this._portId = json.portId
        }
        if (json.values != null) {
            this._values = json.values.slice()
        }
        if (json.delays != null) {
            this._delays = json.delays.slice()
        }
        if (json.repeatCount != null) {
            this._repeatCount = json.repeatCount
        }
    }

}

// TODO es7 class fields
SequencePushButton.category = gettext('Push Buttons')
SequencePushButton.displayName = gettext('Sequence Push Button')
SequencePushButton.typeName = 'SequencePushButton'
SequencePushButton.icon = new StockIcon({name: 'widget-push-button', stockName: 'qtoggle'})
SequencePushButton.ConfigForm = ConfigForm
SequencePushButton.hResizable = true
SequencePushButton.vResizable = true


Widgets.register(SequencePushButton)


export default SequencePushButton
