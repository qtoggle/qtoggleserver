
import $ from '$qui/lib/jquery.module.js'

import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields/common-fields.js'
import {ColorComboField} from '$qui/forms/common-fields/common-fields.js'
import {NumericField}    from '$qui/forms/common-fields/common-fields.js'
import {TextField}       from '$qui/forms/common-fields/common-fields.js'
import {UpDownField}     from '$qui/forms/common-fields/common-fields.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as Theme        from '$qui/theme.js'
import * as ArrayUtils   from '$qui/utils/array.js'
import * as Window       from '$qui/window.js'

import PortPickerField  from '$app/dashboard/widgets/port-picker-field.js'
import Widget           from '$app/dashboard/widgets/widget.js'
import {DEFAULT_COLOR}  from '$app/dashboard/widgets/widget.js'
import WidgetConfigForm from '$app/dashboard/widgets/widget-config-form.js'
import * as Widgets     from '$app/dashboard/widgets/widgets.js'


const SMALL_LABEL_HEIGHT = 0.15 /* em */
const SMALL_LABEL_FONT_SIZE = 0.1 /* em */


class ConfigForm extends WidgetConfigForm {

    constructor({...args}) {
        super({
            fields: [
                new PortPickerField({
                    name: 'portId',
                    label: gettext('Port'),
                    required: true
                }),
                new ColorComboField({
                    name: 'normalColor',
                    label: gettext('Normal Color'),
                    filterEnabled: true,
                    required: true
                }),
                new ColorComboField({
                    name: 'activeColor',
                    label: gettext('Active Color'),
                    filterEnabled: true,
                    required: true
                }),
                new CheckField({
                    name: 'separateColors',
                    label: gettext('Separate Colors'),
                    onChange: (value, form) => form._updateButtonFields()
                }),
                new CheckField({
                    name: 'vertical',
                    label: gettext('Vertical')
                }),
                new UpDownField({
                    name: 'numButtons',
                    label: gettext('Buttons'),
                    min: 2,
                    max: 20,
                    onChange: (value, form) => form._updateButtonFields()
                })
            ],
            ...args
        })
    }

    onUpdateFromWidget() {
        this._updateButtonFields()
    }

    _updateButtonFields() {
        let buttonValueFields =
                this.getFields().filter(field => field.getName().match(new RegExp('buttonValue\\d+')))
        let buttonLabelFields =
                this.getFields().filter(field => field.getName().match(new RegExp('buttonLabel\\d+')))
        let buttonColorFields =
                this.getFields().filter(field => field.getName().match(new RegExp('buttonColor\\d+')))
        let activeColorField = this.getField('activeColor')

        let buttonFields = buttonValueFields.concat(buttonLabelFields).concat(buttonColorFields)

        let data = this.getUnvalidatedData()
        let port = this.getPort(data.portId)

        /* Show/hide active color field */
        if (data.separateColors) {
            activeColorField.hide()
        }
        else {
            activeColorField.show()
        }

        let lastButtonFieldNo = buttonLabelFields.length - 1

        /* Add new needed fields */
        ArrayUtils.range(lastButtonFieldNo + 1, data.numButtons).forEach(function (no) {

            let fields = this._addButtonFields(no, port)

            buttonFields.push(fields.valueField)
            buttonFields.push(fields.labelField)
            buttonFields.push(fields.colorField)

        }, this)

        /* Show all used fields */
        ArrayUtils.range(0, data.numButtons).forEach(function (no) {

            let fields = this._getButtonFields(no)

            fields.valueField.show()
            fields.labelField.show()

            if (data.separateColors) {
                fields.colorField.show()
            }
            else {
                fields.colorField.hide()
            }

        }, this)

        /* Hide all unused fields */
        ArrayUtils.range(data.numButtons, lastButtonFieldNo + 1).forEach(function (no) {

            let fields = this._getButtonFields(no)

            fields.valueField.hide()
            fields.labelField.hide()
            fields.colorField.hide()

        }, this)
    }

    _addButtonFields(no, port) {
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

        let valueField = new NumericField({
            name: `buttonValue${no}`,
            label: `${gettext('Value')} ${no + 1}`,
            required: true,
            separator: true,
            min: min,
            max: max,
            integer: integer,
            step: step
        })

        let labelField = new TextField({
            name: `buttonLabel${no}`,
            label: `${gettext('Label')} ${no + 1}`
        })

        let colorField = new ColorComboField({
            name: `buttonColor${no}`,
            label: `${gettext('Color')} ${no + 1}`,
            filterEnabled: true,
            required: true
        })

        this.addField(-1, valueField)
        this.addField(-1, labelField)
        this.addField(-1, colorField)

        return {
            valueField: valueField,
            labelField: labelField,
            colorField: colorField
        }
    }

    _getButtonFields(no) {
        let valueField = this.getField(`buttonValue${no}`)
        let labelField = this.getField(`buttonLabel${no}`)
        let colorField = this.getField(`buttonColor${no}`)

        return {
            valueField: valueField,
            labelField: labelField,
            colorField: colorField
        }
    }

    fromWidget(widget) {
        let data = super.fromWidget(widget)

        data.numButtons = data.values.length
        ArrayUtils.range(0, data.numButtons).forEach(function (i) {
            data[`buttonValue${i}`] = data.values[i]
            data[`buttonLabel${i}`] = data.labels[i]
            data[`buttonColor${i}`] = data.colors[i]
        })

        return data
    }

    toWidget(data, widget) {
        data.values = []
        data.labels = []
        data.colors = []

        ArrayUtils.range(0, data.numButtons).forEach(function (i) {
            data.values[i] = data[`buttonValue${i}`]
            data.labels[i] = data[`buttonLabel${i}`]
            data.colors[i] = data[`buttonColor${i}`]
        })

        super.toWidget(data, widget)
    }

}


/**
 * @alias qtoggle.dashboard.widgets.pushbuttons.RadioButtons
 * @extends qtoggle.dashboard.widgets.Widget
 */
class RadioButtons extends Widget {

    static category = gettext('Push Buttons')
    static displayName = gettext('Radio Buttons')
    static typeName = 'RadioButtons'
    static icon = new StockIcon({name: 'widget-radio', stockName: 'qtoggle'})
    static ConfigForm = ConfigForm
    static hResizable = false
    static vResizable = false


    /**
     * @constructs
     */
    constructor() {
        super()

        this._normalColor = '@gray-color'
        this._activeColor = DEFAULT_COLOR
        this._separateColors = false
        this._portId = ''
        this._vertical = false

        /* The radio buttons widget requires at least two buttons */
        this._buttons = [
            {value: 0, label: '', color: ''}, {value: 0, label: '', color: ''}
        ]
    }

    isValid() {
        if (!this._portId) {
            return false
        }

        let port = this.getPort(this._portId)

        return Boolean(port && port.enabled && port.writable && port.online !== false && port.type === 'number')
    }

    showCurrentValue() {
        let value = this.getPortValue(this._portId)
        if (value == null) {
            return
        }

        this._showValue(value)
    }

    makeContent(width, height) {
        let container = $('<div></div>', {class: 'dashboard-radio-buttons-container'})
        if (this._vertical) {
            container.addClass('vertical')
        }
        else {
            container.addClass('horizontal')
            container.css('margin-top', `${this._getLabelHeight() + Widgets.CELL_PADDING}em`)
        }

        container.toggleClass('separate-colors', this._separateColors)

        this._buttons.forEach(function (button, index) {

            button.bezelDiv = this._makeBezel(width, height)
            container.append(button.bezelDiv)

            button.labelSpan = this._makeLabel(index)
            button.bezelDiv.append(button.labelSpan)

            button.handleDiv = this._makeHandleDiv(index)
            button.bezelDiv.append(button.handleDiv)

        }, this)

        return container
    }

    _makeLabel(index) {
        let labelSpan = $('<span></span>', {class: 'dashboard-radio-buttons-label'})
        labelSpan.css({
            'font-size': `${this._getLabelFontSize()}em`,
            'top': `${-(this._getLabelHeight() / this._getLabelFontSize())}em`
        })
        labelSpan.text(this._buttons[index].label)

        return labelSpan
    }


    _makeBezel(width, height) {
        let diameter = Math.min(width, height) - this._getLabelHeight() - 2 * Widgets.CELL_PADDING

        let bezelDiv = $('<div></div>', {class: 'dashboard-push-button-bezel'})
        bezelDiv.css({
            width: `${diameter}em`,
            height: `${diameter}em`
        })

        return bezelDiv
    }

    _makeHandleDiv(index) {
        let handleDiv = $('<div></div>', {class: 'qui-base-button dashboard-push-button-handle'})
        handleDiv.css({
            background: Theme.getColor(this._normalColor),
            borderColor: Theme.getColor(this._separateColors ? this._buttons[index].color : this._activeColor),
            margin: `${this.roundEm(Widgets.BEZEL_WIDTH)}em`
        })

        let that = this

        function pointerUp() {
            Window.$body.off('pointerup pointercancel pointerleave', pointerUp)

            that.vibrate()
            that.handleRelease(index)

            if (that._timeoutHandle) {
                clearTimeout(that._timeoutHandle)
                that._timeoutHandle = null
            }
        }

        handleDiv.on('pointerdown', function (e) {
            Window.$body.on('pointerup pointercancel pointerleave', pointerUp)

            that._showValue(that._buttons[index].value)
            that.vibrate()
            that.handlePress(index)

            if (that._timeout) {
                that._timeoutHandle = setTimeout(function () {
                    that._timeoutHandle = null
                    pointerUp()
                }, that._timeout)
            }

            e.preventDefault()
        })

        return handleDiv
    }

    _showValue(value) {
        this._buttons.forEach(function (button) {
            let activeColor = this._separateColors ? button.color : this._activeColor

            if (button.value === value) {
                button.handleDiv.css('background', Theme.getColor(activeColor))
                button.handleDiv.css('border-width', '0')
            }
            else {
                button.handleDiv.css('background', Theme.getColor(this._normalColor))
                button.handleDiv.css('border-width', '')
            }
        }, this)
    }

    _getLabelHeight() {
        if (this.getLabel()) {
            return SMALL_LABEL_HEIGHT
        }
        else {
            return this.constructor.hasFrame ? Widgets.LABEL_HEIGHT_WITH_FRAME : Widgets.LABEL_HEIGHT
        }
    }

    _getLabelFontSize() {
        if (this.getLabel()) {
            return SMALL_LABEL_FONT_SIZE
        }
        else {
            return Widgets.LABEL_FONT_SIZE
        }
    }

    handlePress(index) {
        this.setPortValue(this._portId, this._buttons[index].value)
    }

    handleRelease(index) {
    }

    configToJSON() {
        return {
            normalColor: this._normalColor,
            activeColor: this._activeColor,
            separateColors: this._separateColors,
            portId: this._portId,
            vertical: this._vertical,
            values: this._buttons.map(b => b.value),
            labels: this._buttons.map(b => b.label),
            colors: this._buttons.map(b => b.color)
        }
    }

    configFromJSON(json) {
        if (json.normalColor) {
            this._normalColor = json.normalColor
        }
        if (json.activeColor) {
            this._activeColor = json.activeColor
        }
        if (json.separateColors != null) {
            this._separateColors = json.separateColors
        }
        if (json.portId) {
            this._portId = json.portId
        }
        if (json.vertical != null) {
            this._vertical = json.vertical
        }

        if (json.values != null) {
            this._buttons = json.values.map(function (value, i) {
                return {
                    value: value,
                    label: json.labels != null ? json.labels[i] : '',
                    color: json.colors != null ? json.colors[i] : ''
                }
            })

            if (this._vertical) {
                this.setWidth(1)
                this.setHeight(json.values.length)
            }
            else {
                this.setWidth(json.values.length)
                this.setHeight(1)
            }
        }
    }

    onPortValueChange(portId, value) {
        if (portId !== this._portId) {
            return
        }

        this._showValue(value)
    }

}

Widgets.register(RadioButtons)


export default RadioButtons
