
import $ from '$qui/lib/jquery.module.js'

import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields/common-fields.js'
import {ColorComboField} from '$qui/forms/common-fields/common-fields.js'
import {NumericField}    from '$qui/forms/common-fields/common-fields.js'
import {SliderField}     from '$qui/forms/common-fields/common-fields.js'
import {TextField}       from '$qui/forms/common-fields/common-fields.js'
import {UpDownField}     from '$qui/forms/common-fields/common-fields.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as Theme        from '$qui/theme.js'
import * as ArrayUtils   from '$qui/utils/array.js'
import * as ObjectUtils  from '$qui/utils/object.js'
import * as StringUtils  from '$qui/utils/string.js'

import PortPickerField  from '$app/dashboard/widgets/port-picker-field.js'
import Widget           from '$app/dashboard/widgets/widget.js'
import {DEFAULT_COLOR}  from '$app/dashboard/widgets/widget.js'
import WidgetConfigForm from '$app/dashboard/widgets/widget-config-form.js'
import * as Widgets     from '$app/dashboard/widgets/widgets.js'


const MAX_VALUES_COUNT = 50


class ConfigForm extends WidgetConfigForm {

    constructor({...args}) {
        super({
            fields: [
                new PortPickerField({
                    name: 'portId',
                    label: gettext('Port'),
                    required: true,
                    onChange: (value, form) => form._updateFields()
                }),

                new TextField({
                    name: 'falseText',
                    label: gettext('False Text'),
                    separator: true,
                    required: true
                }),
                new TextField({
                    name: 'trueText',
                    label: gettext('True Text'),
                    required: true
                }),
                new ColorComboField({
                    name: 'falseColor',
                    filterEnabled: true,
                    label: gettext('False Color'),
                    separator: true,
                    required: true
                }),
                new ColorComboField({
                    name: 'trueColor',
                    filterEnabled: true,
                    label: gettext('True Color'),
                    required: true
                }),

                new CheckField({
                    name: 'displayUnit',
                    label: gettext('Display Unit'),
                    separator: true,
                    onChange: (value, form) => form._updateFields()
                }),
                new TextField({
                    name: 'unit',
                    label: gettext('Unit'),
                    maxLength: 16
                }),
                new UpDownField({
                    name: 'decimals',
                    label: gettext('Decimals'),
                    min: 0,
                    max: 10
                }),
                new ColorComboField({
                    name: 'color',
                    filterEnabled: true,
                    label: gettext('Color'),
                    required: true
                }),
                new SliderField({
                    name: 'size',
                    label: gettext('Size'),
                    required: true,
                    ticks: ArrayUtils.range(1, 11).map(i => ({value: i, label: `${i}`}))
                }),

                new CheckField({
                    name: 'customText',
                    label: gettext('Custom Text'),
                    separator: true,
                    onChange: (value, form) => form._updateFields()
                }),
                new TextField({
                    name: 'text',
                    label: gettext('Text'),
                    description: gettext('Use {{value}} as a placeholder for current port value.'),
                    required: true
                }),

                new CheckField({
                    name: 'customValues',
                    label: gettext('Custom Values'),
                    separator: true,
                    onChange: (value, form) => form._updateFields()
                }),
                new UpDownField({
                    name: 'customValuesCount',
                    label: gettext('Number Of Values'),
                    min: 2,
                    max: MAX_VALUES_COUNT,
                    onChange: (value, form) => form._updateFields()
                })
            ],
            ...args
        })
    }

    onUpdateFromWidget() {
        this._updateFields()
    }

    _updateFields() {
        let data = this.getUnvalidatedData()
        let port = this.getPort(data.portId)
        let isBoolean = true
        if (port && port.type === 'number') {
            isBoolean = false
        }

        /* Gather current custom fields */
        let customValuesFields = this.getFields().filter(f => f.getName().match(new RegExp('customValue\\d+')))
        let customTextsFields = this.getFields().filter(f => f.getName().match(new RegExp('customText\\d+')))
        let customColorsFields = this.getFields().filter(f => f.getName().match(new RegExp('customColor\\d+')))

        /* Add new needed custom fields */
        let lastCustomFieldNo = customValuesFields.length - 1
        ArrayUtils.range(lastCustomFieldNo + 1, data.customValuesCount).forEach(function (no) {

            let fields = this._addCustomFields(no, port)

            customValuesFields.push(fields.valueField)
            customTextsFields.push(fields.textField)
            customColorsFields.push(fields.colorField)

        }.bind(this))

        let customFields = [...customValuesFields, ...customTextsFields, ...customColorsFields]
        let customFieldNames = customFields.map(f => f.getName())

        let booleanFieldNames = ['falseText', 'trueText', 'falseColor', 'trueColor']
        let numberFieldNames = [
            'displayUnit',
            'unit',
            'decimals',
            'color',
            'customText',
            'text',
            'customValues',
            'customValuesCount',
            ...customFieldNames
        ]

        let allFieldNames = [...booleanFieldNames, ...numberFieldNames]
        let visibleFieldNames

        if (isBoolean) {
            visibleFieldNames = ObjectUtils.fromEntries(booleanFieldNames.map(f => [f, true]))
        }
        else { /* number */
            visibleFieldNames = ObjectUtils.fromEntries(numberFieldNames.map(f => [f, true]))

            if (data.customText || data.customValues) {
                delete visibleFieldNames['displayUnit']
            }
            if (data.customText || data.customValues || !data.displayUnit) {
                delete visibleFieldNames['unit']
            }
            if (!data.customText || data.customValues) {
                delete visibleFieldNames['text']
            }
            if (data.customValues) {
                delete visibleFieldNames['color']
                delete visibleFieldNames['customText']
            }
            else {
                delete visibleFieldNames['customValuesCount']
                customFieldNames.forEach(n => delete visibleFieldNames[n])
            }

            /* Hide all unused custom fields */
            ArrayUtils.range(data.customValuesCount, lastCustomFieldNo + 1).forEach(function (no) {

                let fields = this._getCustomFields(no)

                delete visibleFieldNames[fields.valueField.getName()]
                delete visibleFieldNames[fields.textField.getName()]
                delete visibleFieldNames[fields.colorField.getName()]

            }.bind(this))
        }

        allFieldNames.forEach(function (name) {
            let field = this.getField(name)
            if (name in visibleFieldNames && field.isHidden()) {
                field.show()
            }
            else if (!(name in visibleFieldNames) && !field.isHidden()) {
                field.hide()
            }
        }.bind(this))
    }

    _addCustomFields(no, port) {
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

        let customValuesCountField = this.getField('customValuesCount')
        let index = this.getFieldIndex(customValuesCountField) + 1 + no * 3

        let valueField = new NumericField({
            name: `customValue${no}`,
            label: `${gettext('Value')} ${no + 1}`,
            required: true,
            separator: true,
            min: min,
            max: max,
            integer: integer,
            step: step
        })
        this.addField(index, valueField)

        let textField = new TextField({
            name: `customText${no}`,
            label: `${gettext('Text')} ${no + 1}`,
            required: true
        })
        this.addField(index + 1, textField)

        let colorField = new ColorComboField({
            name: `customColor${no}`,
            label: `${gettext('Color')} ${no + 1}`,
            filterEnabled: true,
            required: true
        })
        this.addField(index + 2, colorField)

        return {
            valueField: valueField,
            textField: textField,
            colorField: colorField
        }
    }

    _getCustomFields(no) {
        let valueField = this.getField(`customValue${no}`)
        let textField = this.getField(`customText${no}`)
        let colorField = this.getField(`customColor${no}`)

        return {
            valueField: valueField,
            textField: textField,
            colorField: colorField
        }
    }

    fromWidget(widget) {
        let data = super.fromWidget(widget)

        data.customValues.forEach(function (v, no) {
            data[`customValue${no}`] = v.value
            data[`customText${no}`] = v.text
            data[`customColor${no}`] = v.color
        })

        data.customValues = data.customValues.length >= 2
        data.customValuesCount = data.customValues.length

        return data
    }

    toWidget(data, widget) {
        if (data.customValues) {
            data.customValues = ArrayUtils.range(0, data.customValuesCount).map(function (no) {

                return {
                    value: data[`customValue${no}`],
                    text: data[`customText${no}`],
                    color: data[`customColor${no}`]
                }

            })
        }
        else {
            data.customValues = []
        }

        super.toWidget(data, widget)
    }

    fromPort(port, fieldName) {
        let data = super.fromPort(port, fieldName)

        data.unit = port.unit

        return data
    }

}


/**
 * @alias qtoggle.dashboard.widgets.displays.TextIndicator
 * @extends qtoggle.dashboard.widgets.Widget
 */
class TextIndicator extends Widget {

    static category = gettext('Displays')
    static displayName = gettext('Text Indicator')
    static typeName = 'TextIndicator'
    static icon = new StockIcon({name: 'widget-text', stockName: 'qtoggle'})
    static ConfigForm = ConfigForm
    static vResizable = true
    static hResizable = true


    /**
     * @constructs
     */
    constructor() {
        super()

        this._portId = ''

        this._falseText = gettext('Off')
        this._falseColor = '@disabled-color'
        this._trueText = gettext('On')
        this._trueColor = DEFAULT_COLOR

        this._displayUnit = true
        this._unit = ''
        this._decimals = 0
        this._color = DEFAULT_COLOR
        this._size = 5
        this._customText = false
        this._text = '{{value}}'

        this._customValues = []

        this._textElement = null
    }

    isValid() {
        if (!this._portId) {
            return false
        }

        let port = this.getPort(this._portId)

        return Boolean(port && port.enabled && port.online !== false)
    }

    showCurrentValue() {
        let value = this.getPortValue(this._portId)
        if (value == null) {
            return
        }

        this._showValue(value)
    }

    onPortValueChange(portId, value) {
        if (portId !== this._portId) {
            return
        }

        this._showValue(value)
    }

    makeContent(width, height) {
        let container = $('<div></div>', {class: 'dashboard-text-indicator-container'})

        this._textElement = this._makeTextElement(width, height)
        container.append(this._textElement)

        return container
    }

    _makeTextElement(width, height) {
        let textElement = $('<span></span>', {class: 'dashboard-text-indicator-text-element'})

        textElement.css('font-size', `${this._size * 10}%`)

        return textElement
    }

    _showValue(value) {
        let text
        let color

        if (this._isBoolean()) {
            if (value) {
                text = this._trueText
                color = this._trueColor
            }
            else {
                text = this._falseText
                color = this._falseColor
            }
        }
        else { /* Number */
            let valueText = value.toFixed(this._decimals)
            if (this._displayUnit) {
                valueText += this._unit
            }

            if (this._customValues.length) {
                let match = this._customValues.find(m => m.value === value) || this._customValues[0]
                text = match.text
                color = match.color
            }
            else if (this._customText) {
                text = this._text
                color = this._color
            }
            else {
                text = '{{value}}'
                color = this._color
            }

            text = StringUtils.replaceAll(text, '{{value}}', valueText)
        }

        color = Theme.getColor(color)

        this._textElement.css('color', color)
        this._textElement.html(text)
    }

    _isBoolean() {
        let port = this.getPort(this._portId)
        return port && port.type === 'boolean'
    }

    configToJSON() {
        return {
            portId: this._portId,

            falseText: this._falseText,
            falseColor: this._falseColor,
            trueText: this._trueText,
            trueColor: this._trueColor,

            displayUnit: this._displayUnit,
            unit: this._unit,
            decimals: this._decimals,
            color: this._color,
            size: this._size,
            customText: this._customText,
            text: this._text,

            customValues: this._customValues
        }
    }

    configFromJSON(json) {
        if (json.portId) {
            this._portId = json.portId
        }

        if (json.falseText != null) {
            this._falseText = json.falseText
        }
        if (json.trueText != null) {
            this._trueText = json.trueText
        }
        if (json.falseColor != null) {
            this._falseColor = json.falseColor
        }
        if (json.trueColor != null) {
            this._trueColor = json.trueColor
        }

        if (json.displayUnit != null) {
            this._displayUnit = json.displayUnit
        }
        if (json.unit != null) {
            this._unit = json.unit
        }
        if (json.decimals != null) {
            this._decimals = json.decimals
        }
        if (json.color != null) {
            this._color = json.color
        }
        if (json.size != null) {
            this._size = json.size
        }
        if (json.customText != null) {
            this._customText = json.customText
        }
        if (json.text != null) {
            this._text = json.text
        }

        if (json.customValues != null) {
            this._customValues = json.customValues
        }
    }

}

Widgets.register(TextIndicator)


export default TextIndicator
