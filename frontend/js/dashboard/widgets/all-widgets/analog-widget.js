
import $ from '$qui/lib/jquery.module.js'

import {gettext}            from '$qui/base/i18n.js'
import {CheckField}         from '$qui/forms/common-fields.js'
import {ColorComboField}    from '$qui/forms/common-fields.js'
import {NumericField}       from '$qui/forms/common-fields.js'
import {TextField}          from '$qui/forms/common-fields.js'
import {UpDownField}        from '$qui/forms/common-fields.js'
import {ChoiceButtonsField} from '$qui/forms/common-fields.js'
import StockIcon            from '$qui/icons/stock-icon.js'
import * as Theme           from '$qui/theme.js'
import * as ArrayUtils      from '$qui/utils/array.js'
import * as Colors          from '$qui/utils/colors.js'
import * as HTML            from '$qui/utils/html.js'
import * as StringUtils     from '$qui/utils/string.js'

import * as Cache       from '$app/cache.js'
import PortPickerField  from '$app/dashboard/widgets/port-picker-field.js'
import Widget           from '$app/dashboard/widgets/widget.js'
import WidgetConfigForm from '$app/dashboard/widgets/widget-config-form.js'
import * as Widgets     from '$app/dashboard/widgets/widgets.js'


const TEXT_FACTOR = 0.20 /* Fraction of button thickness */
const TICKS_THICKNESS_FACTOR_VERT = 0.30 /* Fraction of button thickness */
const TICKS_THICKNESS_FACTOR_HORIZ = 0.20 /* Fraction of button thickness */

const MIN_TICKS = 2
const MAX_TICKS = 500

const SNAP_NONE = 'none'
const SNAP_LOOSE = 'loose'
const SNAP_STRICT = 'strict'

const LOOSE_SNAP_DIST = 0.1 /* em */


export class ConfigForm extends WidgetConfigForm {

    constructor(widget, readonly) {
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
                new ChoiceButtonsField({
                    name: 'snap',
                    label: gettext('Snapping'),
                    separator: true,
                    required: true,
                    choices: [
                        {label: gettext('None'), value: SNAP_NONE},
                        {label: gettext('Loose'), value: SNAP_LOOSE},
                        {label: gettext('Strict'), value: SNAP_STRICT}
                    ]
                }),
                new CheckField({
                    name: 'displayTicks',
                    label: gettext('Display Ticks'),
                    onChange: (value, form) => form._updateTicksFields()
                }),
                new CheckField({
                    name: 'displayTicksUnits',
                    label: gettext('Display Ticks Units')
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
                })
            ]
        })

        this._readonly = readonly
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

        let displayUnitField = this.getField('displayUnit')
        let displayTicksUnitsField = this.getField('displayTicksUnits')
        let ticksCountField = this.getField('ticksCount')
        let customTicksField = this.getField('customTicks')
        let ticksStepField = this.getField('ticksStep')
        let colorTicksField = this.getField('colorTicks')
        let customTicksFields = customTicksLabelFields.concat(customTicksValueFields)
        let snapField = this.getField('snap')

        let data = this.getUnvalidatedData()
        let port = Cache.getPort(data.portId)

        if (this._readonly) {
            snapField.hide()
        }
        else {
            snapField.show()
        }

        if (data.displayTicks) {
            colorTicksField.show()
            if (this._readonly) {
                displayTicksUnitsField.show()
                ticksStepField.show()
                ticksCountField.show()
                customTicksField.show()
            }
        }
        else {
            colorTicksField.hide()
            if (this._readonly) {
                displayTicksUnitsField.hide()
                ticksStepField.hide()
                ticksCountField.hide()
                customTicksField.hide()
            }
        }

        if (data.customTicks) {
            displayUnitField.hide()
            displayTicksUnitsField.hide()
        }
        else {
            displayUnitField.show()
            displayTicksUnitsField.show()
        }

        if (!data.customTicks || (this._readonly && !data.displayTicks)) {
            customTicksFields.forEach(function (field) {
                field.hide()
            })

            return
        }

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


export class AnalogWidget extends Widget {

    constructor(readonly) {
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
        this._snap = SNAP_STRICT
        this._displayTicks = false
        this._displayTicksUnits = false
        this._colorTicks = false
        this._ticksStep = 1
        this._ticksCount = 0
        this._customTicks = []
        this._readonly = readonly

        this._containerDiv = null
        this._backgroundDiv = null
        this._backgroundCoverDiv = null
        this._ticksDiv = null
        this._cursorDiv = null
        this._handleDiv = null
        this._textDiv = null

        this._thickness = 0
        this._length = 0
        this._vert = false
        this._ticks = []

        /* Used while dragging */
        this._tempValue = null
        this._dragBeginPos = null

        this._widgetName = StringUtils.uncamelize(this.constructor.typeName)
    }

    isValid() {
        if (!this._portId) {
            return false
        }

        let port = this.getPort(this._portId)
        if (!port) {
            return false
        }

        if (port.online === false) {
            return false
        }

        if (!port.enabled) {
            return false
        }

        if (port.type !== 'number') {
            return false
        }

        if (!this._readonly && !port.writable) {
            return false
        }

        return true
    }

    showCurrentValue() {
        let value = this.getPortValue(this._portId)
        if (value == null) {
            return
        }

        this._showValue(value)
    }

    makeContent(width, height) {
        this._containerDiv = $(`<div class="dashboard-analog-widget-container
                                            dashboard-${this._widgetName}-container"></div>`)
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
            this._ticksThicknessFactor = TICKS_THICKNESS_FACTOR_HORIZ
        }
        else {
            this._vert = true
            this._thickness = width
            this._length = height
            this._containerDiv.addClass('vert')
            this._ticksThicknessFactor = TICKS_THICKNESS_FACTOR_VERT

            /* Make a bit more room for ticks if labels are relatively larger */
            let unit = this._displayTicksUnits ? HTML.plainText(this._unit) : ''
            let len = Math.max(
                String(this._start.toFixed(this._decimals) + unit).length,
                String(this._start.toFixed(this._decimals) + unit).length
            )

            this._ticksThicknessFactor *= (1 + 1.5 * (len - 2) / 10)
        }

        if (this._displayTicks) {
            this._thickness *= (1 - this._ticksThicknessFactor)
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
        let backgroundDiv = $(`<div class="dashboard-analog-widget-background
                                           dashboard-${this._widgetName}-background"></div>`)

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

        this._backgroundCoverDiv = $(`<div class="dashboard-analog-widget-background-cover
                                                  dashboard-${this._widgetName}-background-cover"></div>`)
        this._backgroundCoverDiv.css('margin', `${bezelWidth}em`)
        backgroundDiv.append(this._backgroundCoverDiv)

        if (this._readonly) {
            this._cursorDiv = this._makeCursor()
            backgroundDiv.append(this._cursorDiv)
        }
        else {
            this._handleDiv = this._makeHandle()
            backgroundDiv.append(this._handleDiv)

            this.setDragElement(backgroundDiv, this._vert ? 'y' : 'x')
        }

        if (this._displayValue) {
            this._textDiv = this._makeText()
            backgroundDiv.append(this._textDiv)
        }

        return backgroundDiv
    }

    _makeCursor() {
        let cursorDiv = $(`<div class="dashboard-analog-widget-cursor
                                       dashboard-${this._widgetName}-cursor"></div>`)
        let bezelWidth = this.roundEm(Widgets.BEZEL_WIDTH)
        let height = (this._thickness - 2 * (Widgets.CELL_PADDING + bezelWidth))

        cursorDiv.css({
            left: `${bezelWidth}em`,
            height: `${height}em`
        })

        return cursorDiv
    }

    _makeHandle() {
        let handleDiv = $(`<div class="qui-base-button dashboard-analog-widget-handle
                                       dashboard-${this._widgetName}-handle"></div>`)
        let bezelWidth = this.roundEm(Widgets.BEZEL_WIDTH)
        let radius = this._thickness - 2 * Widgets.CELL_PADDING - 4 * bezelWidth

        handleDiv.css({
            'width': `${radius}em`,
            'height': `${radius}em`,
            'margin': `${bezelWidth}em`,
            'border-width': `${bezelWidth}em`
        })

        return handleDiv
    }

    _makeTicks() {
        let ticksThickness = this._thickness * this._ticksThicknessFactor / (1 - this._ticksThicknessFactor)
        let fontSize = TEXT_FACTOR * this._thickness
        let ticksDiv = $(`<div class="dashboard-analog-widget-ticks dashboard-${this._widgetName}-ticks"></div>`)

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
            /* Determine the position factor */
            let factor = this._valueToFactor(tick.value) /* Yes, factor */

            /* Also set the tick pos & factor */
            tick.pos = this._valueToPos(this._factorToValue(factor))
            tick.factor = factor

            if (i % this._ticksStep !== 0) {
                return
            }

            let labelDiv = $(`<div class="dashboard-analog-widget-tick
                                          dashboard-${this._widgetName}-tick">${tick.label}</div>`)
            labelDiv.css('font-size', `${fontSize}em`)

            if (this._colorTicks) {
                labelDiv.css('color', this._valueToColor(tick.value))
            }

            ticksDiv.append(labelDiv)

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
        let textDiv = $(`<div class="dashboard-analog-widget-text dashboard-${this._widgetName}-text"></div>`)

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
        if (this._vert && this._ticksThicknessFactor / TICKS_THICKNESS_FACTOR_VERT > 1.5) {
            textDiv.css('transform', 'rotate(-90deg)')
        }

        return textDiv
    }

    _showValue(value, pos = null) {
        if (this._start < this._end) {
            value = Math.min(Math.max(value, this._start), this._end)
        }
        else {
            value = Math.min(Math.max(value, this._end), this._start)
        }

        let color = this._valueToColor(value)

        if (this._cursorDiv) {
            let startColor = this._valueToColor(this._start)
            let direction = this._vert ? 'to top' : 'to right'
            let backgroundGradient = `linear-gradient(${direction}, ${startColor}, ${color})`
            this._cursorDiv.css('background', backgroundGradient)
        }

        if (this._handleDiv) {
            this._handleDiv.css('background', color)
        }

        let cellPadding = this.roundEm(Widgets.CELL_PADDING)
        let bezelWidth = this.roundEm(Widgets.BEZEL_WIDTH)

        let tick = this._ticks.find(t => t.value === value)
        let factor
        if (tick) {
            factor = tick.factor
            if (pos == null) {
                pos = tick.pos
            }
        }
        else {
            factor = this._valueToFactor(value)
            if (pos == null) {
                pos = this._valueToPos(value)
            }
        }

        this._containerDiv.toggleClass('end-half', factor > 0.5)

        if (this._vert) {
            if (this._cursorDiv) {
                this._cursorDiv.css('height', `${pos}em`)
            }
            if (this._handleDiv) {
                this._handleDiv.css('bottom', `${pos}em`)
            }
            if (!this._readonly) {
                this._backgroundCoverDiv.css('bottom', `${pos}em`)
            }
        }
        else {
            if (this._cursorDiv) {
                this._cursorDiv.css('width', `${pos}em`)
            }
            if (this._handleDiv) {
                this._handleDiv.css('left', `${pos}em`)
            }
            if (!this._readonly) {
                this._backgroundCoverDiv.css('left', `${pos}em`)
            }
        }

        if (this._textDiv) {
            let valueStr = tick ? tick.label : value.toFixed(this._decimals)
            if (!this._customTicks.length && this._displayUnit && !tick) {
                valueStr += this._unit
            }

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

    _factorToValue(factor) {
        return this._start + factor * (this._end - this._start)
    }

    _valueToPos(value) {
        let factor = this._valueToFactor(value)
        return this._getUsefulLength() * factor
    }

    _posToValue(pos) {
        let factor = pos / this._getUsefulLength()
        return this._factorToValue(factor)
    }

    _valueToColor(value) {
        return Colors.mix(Theme.getColor(this._startColor), Theme.getColor(this._endColor), this._valueToFactor(value))
    }

    _snapPos(pos) {
        if (!this._ticks.length || this._snap === SNAP_NONE) {
            /* Nothing to snap (to) */
            return {
                snapped: false,
                pos: pos,
                dragPos: pos,
                tick: null
            }
        }

        let minDist = Infinity
        let bestTickIndex = 0
        let snapped = false
        let dragPos = pos
        let tick = null

        this._ticks.forEach(function (tick, i) {
            let dist = Math.abs(tick.pos - pos)
            if (dist < minDist) {
                minDist = dist
                bestTickIndex = i
            }
        })

        if (minDist < LOOSE_SNAP_DIST) {
            tick = this._ticks[bestTickIndex]
            pos = dragPos = tick.pos
            snapped = true
        }
        if (this._snap === SNAP_STRICT) {
            tick = this._ticks[bestTickIndex]
            pos = tick.pos
            snapped = true
        }

        return {
            snapped: snapped,
            pos: pos,
            dragPos: dragPos,
            tick: tick
        }
    }

    _getCurPos() {
        if (this._vert) {
            return parseFloat(this._handleDiv[0].style.bottom)
        }
        else {
            return parseFloat(this._handleDiv[0].style.left)
        }
    }

    _setPortValue(value) {
        /* See if port requires integer numbers */
        let port = this.getPort(this._portId)
        if (port && port.integer) {
            value = Math.round(value)
        }

        /* Actually send the new value to the server */
        this.setPortValue(this._portId, value)
    }

    _getUsefulLength() {
        let length = this._length
        if (this._handleDiv) {
            length -= this._thickness
        }
        else {
            length -= (4 * this.roundEm(Widgets.BEZEL_WIDTH) + 2 * Widgets.CELL_PADDING)
        }

        return length
    }

    onDragBegin() {
        this._handleDiv.css('transition', 'none') /* Temporarily disable transitions */
        this._dragBeginPos = this._getCurPos()
        this._tempValue = this._posToValue(this._dragBeginPos)
    }

    onDrag(elemX, elemY, deltaX, deltaY) {
        let deltaPos = this._vert ? -deltaY : deltaX

        /* Compute & limit position */
        let pos = this._dragBeginPos + deltaPos
        pos = Math.min(Math.max(pos, 0), this._getUsefulLength())

        /* Snap position */
        let snapInfo = this._snapPos(pos)
        let value
        if (snapInfo.tick) {
            value = snapInfo.tick.value
        }
        else {
            value = this._posToValue(snapInfo.pos)
        }
        this._showValue(value, snapInfo.dragPos)

        if (Math.abs(value - this._tempValue) < 1e-6) {
            return
        }

        this._tempValue = value

        if (snapInfo.snapped) {
            this.vibrate()
        }
    }

    onDragEnd(elemX, elemY, deltaX, deltaY) {
        this._handleDiv.css('transition', '') /* Restore transitions */

        /* Don't set the value unless the cursor was actually moved */
        if ((this._vert && deltaY === 0) || (!this._vert && deltaX === 0)) {
            return
        }

        let pos = this._getCurPos()
        let snapInfo = this._snapPos(pos)
        let value
        if (snapInfo.tick) {
            value = snapInfo.tick.value
        }
        else {
            value = this._posToValue(snapInfo.pos)
        }

        this._showValue(value)

        /* Don't set the value unless it changed */
        let oldValue = this.getPortValue(this._portId)
        if (value === oldValue) {
            return
        }

        this._setPortValue(value)
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
            snap: this._snap,
            displayTicks: this._displayTicks,
            displayTicksUnits: this._displayTicksUnits,
            colorTicks: this._colorTicks,
            ticksStep: this._ticksStep,
            ticksCount: this._ticksCount,
            customTicks: this._customTicks
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
        if (json.snap != null) {
            this._snap = json.snap
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
    }

    onPortValueChange(portId, value) {
        if (portId !== this._portId) {
            return
        }

        if (this.isDragging()) {
            return
        }

        this._showValue(value)
    }

}

// TODO es7 class fields
AnalogWidget.category = gettext('Displays')
AnalogWidget.displayName = gettext('Progress Bar')
AnalogWidget.typeName = 'ProgressBar'
AnalogWidget.icon = new StockIcon({name: 'widget', stockName: 'qtoggle'})
AnalogWidget.ConfigForm = ConfigForm
AnalogWidget.vResizable = true
AnalogWidget.hResizable = true
AnalogWidget.width = 2
