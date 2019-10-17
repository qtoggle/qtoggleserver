
import $ from '$qui/lib/jquery.module.js'

import {gettext}       from '$qui/base/i18n.js'
import {
    CheckField, ColorComboField, NumericField, TextField, UpDownField
}                      from '$qui/forms/common-fields.js'
import StockIcon       from '$qui/icons/stock-icon.js'
import * as Theme      from '$qui/theme.js'
import * as ArrayUtils from '$qui/utils/array.js'
import * as Colors     from '$qui/utils/colors.js'
import * as HTML       from '$qui/utils/html.js'

import * as Cache       from '$app/cache.js'
import PortPickerField  from '$app/dashboard/widgets/port-picker-field.js'
import Widget           from '$app/dashboard/widgets/widget.js'
import WidgetConfigForm from '$app/dashboard/widgets/widget-config-form.js'
import * as Widgets     from '$app/dashboard/widgets/widgets.js'


const TEXT_FACTOR = 0.20 /* Fraction of button thickness */
const TICKS_FACTOR_VERT = 0.30 /* Fraction of button thickness */
const TICKS_FACTOR_HORIZ = 0.20 /* Fraction of button thickness */

const MIN_TICKS = 2
const MAX_TICKS = 500

/**
 * @class QToggle.DashboardSection.Widgets.ProgressBar.ConfigForm
 * @extends QToggle.DashboardSection.Widgets.WidgetConfigForm
 * @param {QToggle.DashboardSection.Widgets.Widget} widget
 */
export class ConfigForm extends WidgetConfigForm {

    constructor(widget) {
        super(widget, {
            fields: [
                new PortPickerField({
                    name: 'portId',
                    label: gettext('Port'),
                    required: true,
                    filter: port => port.type === 'number' && port.enabled
                }),
                new NumericField({
                    name: 'start',
                    label: gettext('Start Value'),
                    required: true
                }),
                new NumericField({
                    name: 'end',
                    label: gettext('End Value'),
                    required: true
                }),
                new ColorComboField({
                    name: 'startColor',
                    label: gettext('Start Color'),
                    required: true
                }),
                new ColorComboField({
                    name: 'endColor',
                    label: gettext('End Color'),
                    required: true
                }),
                new CheckField({
                    name: 'displayValue',
                    label: gettext('Display Value'),
                    onChange: (value, form) => form._updateDisplayUnitField()
                }),
                new CheckField({
                    name: 'displayUnit',
                    label: gettext('Display Unit')
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
                    max: 3
                }),
                new CheckField({
                    name: 'displayTicks',
                    label: gettext('Display Ticks'),
                    onChange: (value, form) => form._updateTicksFields()
                }),
                new CheckField({
                    name: 'displayTicksUnits',
                    label: gettext('Display Ticks Units'),
                    onChange: (value, form) => form._updateTicksFields()
                }),
                new CheckField({
                    name: 'colorTicks',
                    label: gettext('Color Tick Labels')
                }),
                new UpDownField({
                    name: 'ticksStep',
                    label: gettext('Ticks Step'),
                    min: 1,
                    max: 10
                }),
                new UpDownField({
                    name: 'ticksCount',
                    label: gettext('Ticks'),
                    min: MIN_TICKS,
                    max: MAX_TICKS,
                    onChange: (value, form) => form._updateTicksFields()
                }),
                new CheckField({
                    name: 'customTicks',
                    label: gettext('Custom Ticks'),
                    onChange: (value, form) => form._updateTicksFields()
                }),
                new CheckField({
                    name: 'equidistantTicks',
                    label: gettext('Equidistant Ticks')
                })
            ]
        })
    }

    onUpdateFromWidget() {
        this._updateTicksFields()
        this._updateDisplayUnitField()
    }

    _updateDisplayUnitField() {
        let data = this.getUnvalidatedData()
        if (data.displayValue) {
            this.getField('displayUnit').show()
        }
        else {
            this.getField('displayUnit').hide()
        }
    }

    _updateTicksFields() {
        let customTicksValueFields =
                this.getFields().filter(field => field.getName().match(new RegExp('tickValue\\d+')))
        let customTicksLabelFields =
                this.getFields().filter(field => field.getName().match(new RegExp('tickLabel\\d+')))

        let ticksCountField = this.getField('ticksCount')
        let customTicksField = this.getField('customTicks')
        let ticksStepField = this.getField('ticksStep')
        let colorTicksField = this.getField('colorTicks')
        let customTicksFields = customTicksLabelFields.concat(customTicksValueFields)
        let equidistantTicksField = this.getField('equidistantTicks')

        let data = this.getUnvalidatedData()
        let port = Cache.getPort(data.portId)

        if (data.displayTicks) {
            ticksStepField.show()
            colorTicksField.show()
            ticksCountField.show()
            customTicksField.show()
        }
        else {
            ticksStepField.hide()
            colorTicksField.hide()
            ticksCountField.hide()
            customTicksField.hide()
        }

        if (!data.customTicks || !data.displayTicks) {
            customTicksFields.forEach(function (field) {
                field.hide()
            })

            equidistantTicksField.hide()

            return
        }

        equidistantTicksField.show()

        let lastTickFieldNo = customTicksLabelFields.length - 1

        /* Add new needed fields */
        ArrayUtils.range(lastTickFieldNo + 1, data.ticksCount).forEach(function (no) {

            let fields = this._addTickFields(no, port)

            customTicksFields.push(fields.valueField)
            customTicksFields.push(fields.labelField)

        }, this)

        /* Show all used fields */
        ArrayUtils.range(0, data.ticksCount).forEach(function (no) {

            let fields = this._getTickFields(no)

            fields.valueField.show()
            fields.labelField.show()

        }, this)

        /* Hide all unused fields */
        ArrayUtils.range(data.ticksCount, lastTickFieldNo + 1).forEach(function (no) {

            let fields = this._getTickFields(no)

            fields.valueField.hide()
            fields.labelField.hide()

        }, this)
    }

    _addTickFields(no, port) {
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
            name: `tickValue${no}`,
            label: `${gettext('Tick Value')} ${no + 1}`,
            required: true,
            separator: true,
            min: min,
            max: max,
            integer: integer,
            step: step
        })

        let labelField = new TextField({
            name: `tickLabel${no}`,
            label: `${gettext('Tick Label')} ${no + 1}`
        })

        this.addField(-1, valueField)
        this.addField(-1, labelField)

        return {
            valueField: valueField,
            labelField: labelField
        }
    }

    _getTickFields(no) {
        let valueField = this.getField(`tickValue${no}`)
        let labelField = this.getField(`tickLabel${no}`)

        return {
            valueField: valueField,
            labelField: labelField
        }
    }

    fromWidget(widget) {
        let data = super.fromWidget(widget)

        data.customTicks.forEach(function (t, no) {
            data[`tickValue${no}`] = t.value
            data[`tickLabel${no}`] = t.label
        })

        data.customTicks = Boolean(data.customTicks.length)

        return data
    }

    toWidget(data, widget) {
        if (data.customTicks) {
            data.customTicks = ArrayUtils.range(0, data.ticksCount).map(function (no) {
                return {
                    value: data[`tickValue${no}`],
                    label: data[`tickLabel${no}`]
                }
            })
        }
        else {
            data.customTicks = []
        }

        super.toWidget(data, widget)
    }

    fromPort(port) {
        let data = super.fromPort(port)

        data.unit = port.unit
        data.start = port.min != null ? port.min : 0
        data.end = port.max != null ? port.max : 100

        return data
    }

}


/**
 * @class QToggle.DashboardSection.Widgets.ProgressBar
 * @extends QToggle.DashboardSection.Widgets.Widget
 */
export default class ProgressBar extends Widget {

    constructor() {
        super()

        this._portId = ''
        this._start = 0
        this._end = 100
        this._startColor = '@disabled-color'
        this._endColor = '@interactive-color'
        this._displayValue = true
        this._displayUnit = true
        this._unit = ''
        this._decimals = 0
        this._displayTicks = false
        this._displayTicksUnits = false
        this._colorTicks = false
        this._ticksStep = 1
        this._ticksCount = 0
        this._customTicks = []
        this._equidistantTicks = false

        this._containerDiv = null
        this._backgroundDiv = null
        this._ticksDiv = null
        this._cursorDiv = null
        this._textDiv = null

        this._thickness = 0
        this._length = 0
        this._vert = false
        this._ticks = []
    }

    isValid() {
        if (!this._portId) {
            return false
        }

        let port = this.getPort(this._portId)
        if (!port) {
            return false
        }

        return (port.online !== false) && port.enabled && port.type === 'number'
    }

    showCurrentValue() {
        let value = this.getPortValue(this._portId)
        if (value == null) {
            return
        }

        this._showValue(value)
    }

    makeContent(width, height) {
        this._containerDiv = $('<div class="dashboard-progress-bar-container"></div>')
        this._containerDiv.css({
            top: '0em',
            left: '0em',
            width: `${width}em`,
            height: `${height}em`,
            borderWidth: `${this.roundEm(Widgets.CELL_PADDING)}em`
        })

        if (width > height) {
            this._vert = false
            this._thickness = height
            this._length = width
            this._ticksFactor = TICKS_FACTOR_HORIZ
        }
        else {
            this._vert = true
            this._thickness = width
            this._length = height
            this._containerDiv.addClass('vert')
            this._ticksFactor = TICKS_FACTOR_VERT

            /* Make a bit more room for ticks if labels are relatively larger */
            let unit = this._displayTicksUnits ? HTML.plainText(this._unit) : ''
            let len = Math.max(
                String(this._start.toFixed(this._decimals) + unit).length,
                String(this._start.toFixed(this._decimals) + unit).length
            )

            this._ticksFactor *= (1 + 1.5 * (len - 2) / 10)
        }

        if (this._displayTicks) {
            this._thickness *= (1 - this._ticksFactor)
        }
        this._ticksDiv = this._makeTicks()
        if (this._displayTicks) {
            this._containerDiv.append(this._ticksDiv)
        }

        this._backgroundDiv = this._makeBackground()
        this._containerDiv.append(this._backgroundDiv)

        /* Set an initial state */
        this._showValue(this._start)

        return this._containerDiv
    }

    _makeBackground() {
        let backgroundDiv = $('<div class="dashboard-progress-bar-background"></div>')

        backgroundDiv.css('border-radius', `${Math.min(this.getContentWidth(), this.getContentHeight())}em`)

        let backgroundThickness = this._thickness - 2 * Widgets.CELL_PADDING
        let bezelWidth = this.roundEm(Widgets.BEZEL_WIDTH)

        backgroundDiv.css(this._vert ? 'width' : 'height', `${backgroundThickness}em`)
        backgroundDiv.css('border-width', `${bezelWidth}em`)

        let startColor = this._valueToColor(this._start)
        let endColor = this._valueToColor(this._end)
        let direction = this._vert ? 'to top' : 'to right'
        let backgroundGradient = `linear-gradient(${direction}, ${startColor}, ${endColor})`
        backgroundDiv.css('background', backgroundGradient)

        let backgroundCover = $('<div class="dashboard-progress-bar-background-cover"></div>')
        backgroundCover.css('margin', `${bezelWidth}em`)
        backgroundDiv.append(backgroundCover)

        this._cursorDiv = this._makeCursor()
        backgroundDiv.append(this._cursorDiv)

        if (this._displayValue) {
            this._textDiv = this._makeText()
            backgroundDiv.append(this._textDiv)
        }

        return backgroundDiv
    }

    _makeCursor() {
        let cursorDiv = $('<div class="dashboard-progress-bar-cursor"></div>')
        let bezelWidth = this.roundEm(Widgets.BEZEL_WIDTH)
        let height = (this._thickness - 2 * (Widgets.CELL_PADDING + bezelWidth))

        cursorDiv.css({
            height: `${height}em`
        })

        return cursorDiv
    }

    _makeTicks() {
        let ticksThickness = this._thickness * this._ticksFactor / (1 - this._ticksFactor)
        let fontSize = TEXT_FACTOR * this._thickness
        let ticksDiv = $('<div class="dashboard-progress-bar-ticks"></div>')

        if (this._vert) {
            ticksDiv.css({
                'height': `${(this._length - this._thickness)}em`,
                'width': `${ticksThickness}em`,
                'margin-top': `${(this._thickness / 2 - Widgets.CELL_PADDING)}em`
            })
        }
        else {
            ticksDiv.css({
                'height': `${ticksThickness}em`,
                'margin-left': `${(this._thickness / 2 - Widgets.CELL_PADDING)}em`,
                'margin-right': `${(this._thickness / 2 - Widgets.CELL_PADDING)}em`
            })
        }

        /* Prepare tick values/labels */
        if (this._customTicks.length) {
            this._ticks = this._customTicks.slice()
        }
        else {
            this._ticks = []
            let label, value, step = (this._end - this._start) / (this._ticksCount - 1)
            for (let i = 0; i < this._ticksCount; i++) {
                if (i < this._ticksCount - 1) {
                    value = this._start + i * step
                }
                else {
                    value = this._end
                }

                label = value.toFixed(this._decimals)
                if (this._displayTicksUnits) {
                    label += this._unit
                }
                this._ticks.push({value: value, label: label})
            }
        }

        /* Add tick labels to container */
        this._ticks.forEach(function (tick, i) {
            tick.pos = this._valueToPos(tick.value) /* Also compute the tick pos */

            if (i % this._ticksStep !== 0) {
                return
            }

            let labelDiv = $(`<div class="dashboard-progress-bar-tick">${tick.label}</div>`)
            labelDiv.css('font-size', `${fontSize}em`)

            if (this._colorTicks) {
                labelDiv.css('color', this._valueToColor(tick.value))
            }

            ticksDiv.append(labelDiv)

            /* Determine the position factor */
            let factor
            if (this._equidistantTicks && this._customTicks.length) {
                factor = i / (this._ticks.length - 1)
            }
            else {
                factor = this._valueToFactor(tick.value) /* Yes, factor */
            }

            if (this._vert) {
                labelDiv.css({
                    'top': `${((1 - factor) * 100 - 15)}%`,
                    'line-height': `${(this._length - this._thickness) * 0.3 / fontSize}em`
                })
            }
            else {
                labelDiv.css('left', `${(factor * 100 - 15)}%`)
            }

        }, this)

        return ticksDiv
    }

    _makeText() {
        let textDiv = $('<div class="dashboard-progress-bar-text"></div>')

        let fontSize = TEXT_FACTOR * this._thickness

        textDiv.css({
            'font-size': `${fontSize}em`
        })

        if (this._vert) {
            textDiv.css('width', '100%')
        }
        else {
            textDiv.css('height', '100%')
        }

        /* Rotate longer current value texts on vertical widgets */
        if (this._vert && this._ticksFactor / TICKS_FACTOR_VERT > 1.5) {
            textDiv.css('transform', 'rotate(-90deg)')
        }

        return textDiv
    }

    _showValue(value) {
        if (this._start < this._end) {
            value = Math.min(Math.max(value, this._start), this._end)
        }
        else {
            value = Math.min(Math.max(value, this._end), this._start)
        }

        let startColor = this._valueToColor(this._start)
        let color = this._valueToColor(value)
        let direction = this._vert ? 'to top' : 'to right'
        let backgroundGradient = `linear-gradient(${direction}, ${startColor}, ${color})`
        this._cursorDiv.css('background', backgroundGradient)

        let cellPadding = this.roundEm(Widgets.CELL_PADDING)
        let bezelWidth = this.roundEm(Widgets.BEZEL_WIDTH)
        let factor = this._valueToFactor(value)
        let maxPos = (this._length - 2 * (bezelWidth + cellPadding))
        let pos = maxPos * factor

        this._containerDiv.toggleClass('end-half', factor > 0.5)

        if (this._vert) {
            this._cursorDiv.css('height', `${pos}em`)
        }
        else {
            this._cursorDiv.css('width', `${pos}em`)
        }

        if (this._textDiv) {
            let valueStr = value.toFixed(this._decimals) + (this._displayUnit ? this._unit : '')
            this._textDiv.html(valueStr)

            let fontSize = TEXT_FACTOR * this._thickness
            factor = 1 - factor
            let offs = factor > 0.5 ? factor : (1 - factor)
            let length = (this._length * offs) / fontSize

            this._textDiv.css(this._vert ? 'height' : 'width', `${length}em`)

            let foregroundColor = Theme.getColor('@foreground-color')
            let backgroundColor = Theme.getColor('@background-color')

            let foregroundRGB = Colors.str2rgba(foregroundColor)
            let colorRGB = Colors.str2rgba(color)

            this._textDiv.css('color', foregroundColor)

            if (this._containerDiv.hasClass('end-half')) {
                if (Colors.contrast(foregroundRGB, colorRGB) < 1.5) {
                    this._textDiv.css('color', backgroundColor)
                }
            }
        }
    }

    _valueToFactor(value) {
        return (value - this._start) / (this._end - this._start)
    }

    _valueToPos(value) {
        let factor = this._valueToFactor(value)
        return (this._length - this._thickness) * factor
    }

    _valueToColor(value) {
        return Colors.mix(Theme.getColor(this._startColor), Theme.getColor(this._endColor), this._valueToFactor(value))
    }

    configToJSON() {
        return {
            portId: this._portId,
            start: this._start,
            end: this._end,
            startColor: this._startColor,
            endColor: this._endColor,
            displayValue: this._displayValue,
            displayUnit: this._displayUnit,
            unit: this._unit,
            decimals: this._decimals,
            displayTicks: this._displayTicks,
            displayTicksUnits: this._displayTicksUnits,
            colorTicks: this._colorTicks,
            ticksStep: this._ticksStep,
            ticksCount: this._ticksCount,
            customTicks: this._customTicks,
            equidistantTicks: this._equidistantTicks
        }
    }

    configFromJSON(json) {
        if (json.portId) {
            this._portId = json.portId
        }
        if (json.start != null) {
            this._start = json.start
        }
        if (json.end != null) {
            this._end = json.end
        }
        if (json.startColor) {
            this._startColor = json.startColor
        }
        if (json.endColor) {
            this._endColor = json.endColor
        }
        if (json.displayValue != null) {
            this._displayValue = json.displayValue
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
        if (json.displayTicks != null) {
            this._displayTicks = json.displayTicks
        }
        if (json.displayTicksUnits != null) {
            this._displayTicksUnits = json.displayTicksUnits
        }
        if (json.colorTicks != null) {
            this._colorTicks = json.colorTicks
        }
        if (json.ticksStep != null) {
            this._ticksStep = json.ticksStep
        }
        if (json.ticksCount != null) {
            this._ticksCount = json.ticksCount
        }
        if (json.customTicks != null) {
            this._customTicks = json.customTicks.slice()
        }
        if (json.equidistantTicks != null) {
            this._equidistantTicks = json.equidistantTicks
        }
    }

    onPortValueChange(portId, value) {
        if (portId !== this._portId) {
            return
        }

        this._showValue(value)
    }

}

// TODO es7 class fields
ProgressBar.category = gettext('Displays')
ProgressBar.displayName = gettext('Progress Bar')
ProgressBar.typeName = 'ProgressBar'
ProgressBar.icon = new StockIcon({name: 'widget', stockName: 'qtoggle'})
ProgressBar.ConfigForm = ConfigForm
ProgressBar.vResizable = true
ProgressBar.hResizable = true
ProgressBar.width = 2


Widgets.register(ProgressBar)
