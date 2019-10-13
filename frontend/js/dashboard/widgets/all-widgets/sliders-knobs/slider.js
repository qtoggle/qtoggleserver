
import $ from '$qui/lib/jquery.module.js'

import {gettext}    from '$qui/base/i18n.js'
import {ComboField} from '$qui/forms/common-fields.js'
import StockIcon    from '$qui/icons/stock-icon.js'
import * as Colors  from '$qui/utils/colors.js'
import * as HTML    from '$qui/utils/html.js'
import * as Theme   from '$qui/theme.js'

import Widget       from '$app/dashboard/widgets/widget.js'
import * as Widgets from '$app/dashboard/widgets/widgets.js'

import {ConfigForm as ProgressBarConfigForm} from '../displays/progress-bar.js'


const TEXT_FACTOR = 0.20 /* Fraction of button thickness */
const TICKS_FACTOR_VERT = 0.30 /* Fraction of button thickness */
const TICKS_FACTOR_HORIZ = 0.20 /* Fraction of button thickness */

const SNAP_NONE = 'none'
const SNAP_LOOSE = 'loose'
const SNAP_STRICT = 'strict'

const LOOSE_SNAP_DIST = 0.1 /* em */


/**
 * @class QToggle.DashboardSection.Widgets.Slider.ConfigForm
 * @extends QToggle.DashboardSection.Widgets.ProgressBar.ConfigForm
 * @param {QToggle.DashboardSection.Widgets.Widget} widget
 */
class ConfigForm extends ProgressBarConfigForm {

    constructor(widget) {
        super(widget)

        this.addField(8, new ComboField({
            name: 'snap',
            label: gettext('Snapping'),
            separator: true,
            required: true,
            choices: [
                {label: gettext('None'), value: SNAP_NONE},
                {label: gettext('Loose'), value: SNAP_LOOSE},
                {label: gettext('Strict'), value: SNAP_STRICT}
            ]
        }))
    }

}


/**
 * @class QToggle.DashboardSection.Widgets.Slider
 * @extends QToggle.DashboardSection.Widgets.Widget
 */
export default class Slider extends Widget {

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
        this._snap = SNAP_STRICT
        this._displayTicks = false
        this._displayTicksUnits = false
        this._colorTicks = false
        this._ticksStep = 1
        this._ticksCount = 0
        this._customTicks = []
        this._equidistantTicks = false

        this._containerDiv = null
        this._backgroundDiv = null
        this._backgroundCoverDiv = null
        this._ticksDiv = null
        this._handleDiv = null
        this._textDiv = null

        this._thickness = 0
        this._length = 0
        this._vert = false
        this._ticks = []

        /* Used while dragging */
        this._tempValue = null
        this._dragBeginPos = null
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
        this._containerDiv = $('<div class="dashboard-slider-container"></div>')
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
        let backgroundDiv = $('<div class="dashboard-slider-background"></div>')

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

        this._backgroundCoverDiv = $('<div class="dashboard-slider-background-cover"></div>')
        this._backgroundCoverDiv.css('margin', `${bezelWidth}em`)
        backgroundDiv.append(this._backgroundCoverDiv)

        if (this._displayValue) {
            this._textDiv = this._makeText()
            backgroundDiv.append(this._textDiv)
        }

        this._handleDiv = this._makeHandle()
        backgroundDiv.append(this._handleDiv)

        this.setDragElement(backgroundDiv, this._vert ? 'y' : 'x')

        return backgroundDiv
    }

    _makeHandle() {
        let handleDiv = $('<div class="qui-base-button dashboard-slider-handle"></div>')
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
        let ticksThickness = this._thickness * this._ticksFactor / (1 - this._ticksFactor)
        let fontSize = TEXT_FACTOR * this._thickness
        let ticksDiv = $('<div class="dashboard-slider-ticks"></div>')

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

            let labelDiv = $(`<div class="dashboard-slider-tick">${tick.label}</div>`)
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
        let textDiv = $('<div class="dashboard-slider-text"></div>')

        let fontSize = TEXT_FACTOR * this._thickness

        textDiv.css('font-size', `${fontSize}em`)

        if (this._vert) {
            textDiv.css('width', '100%')
        }
        else {
            textDiv.css('height', '100%')
        }

        /* Rotate longer current value texts on vertical sliders */
        if (this._vert && this._ticksFactor / TICKS_FACTOR_VERT > 1.5) {
            textDiv.css('transform', 'rotate(-90deg)')
        }

        return textDiv
    }

    _showValue(value, pos, tick) {
        if (this._start < this._end) {
            value = Math.min(Math.max(value, this._start), this._end)
        }
        else {
            value = Math.min(Math.max(value, this._end), this._start)
        }

        this._handleDiv.css('background', this._valueToColor(value))

        let factor = this._valueToFactor(value)
        if (pos == null) {
            pos = this._valueToPos(value)
        }
        if (tick == null) {
            tick = this._snapPos(pos).tick
        }

        this._containerDiv.toggleClass('end-half', factor > 0.5)

        if (this._vert) {
            this._handleDiv.css('bottom', `${pos}em`)
            this._backgroundCoverDiv.css('bottom', `${pos}em`)
        }
        else {
            this._handleDiv.css('left', `${pos}em`)
            this._backgroundCoverDiv.css('left', `${pos}em`)
        }

        if (this._textDiv) {
            let valueStr = tick ? tick.label : value.toFixed(this._decimals)
            if (this._displayUnit) {
                valueStr += this._unit
            }

            this._textDiv.html(valueStr)

            let fontSize = TEXT_FACTOR * this._thickness
            let offs = factor > 0.5 ? factor : (1 - factor)
            let length = (this._length * offs) / fontSize

            if (this._vert) {
                this._textDiv.css({
                    'height': `${length}em`,
                    'line-height': `${length}em`
                })
            }
            else {
                this._textDiv.css('width', `${length}em`)
            }

            let color = this._valueToColor(value)
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
        return (this._length - this._thickness) * factor
    }

    _posToValue(pos) {
        let factor = pos / (this._length - this._thickness)
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

    onDragBegin() {
        this._handleDiv.css('transition', 'none') /* Temporarily disable transitions */
        this._dragBeginPos = this._getCurPos()
        this._tempValue = this._posToValue(this._dragBeginPos)
    }

    onDrag(elemX, elemY, deltaX, deltaY) {
        let deltaPos = this._vert ? -deltaY : deltaX

        /* Compute & limit position */
        let pos = this._dragBeginPos + deltaPos
        pos = Math.min(Math.max(pos, 0), this._length - this._thickness)

        /* Snap position */
        let snapInfo = this._snapPos(pos)

        let value = this._posToValue(snapInfo.pos)
        this._showValue(value, snapInfo.dragPos, snapInfo.tick)

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

        let pos = this._getCurPos()
        let snapInfo = this._snapPos(pos)
        let value = this._posToValue(snapInfo.pos)

        /* Don't set the value unless the cursor was actually moved */
        if ((this._vert && deltaY === 0) || (!this._vert && deltaX === 0)) {
            return
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
        if (json.equidistantTicks != null) {
            this._equidistantTicks = json.equidistantTicks
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
Slider.category = gettext('Sliders/Knobs')
Slider.displayName = gettext('Slider')
Slider.typeName = 'Slider'
Slider.icon = new StockIcon({name: 'widget', stockName: 'qtoggle'})
Slider.ConfigForm = ConfigForm
Slider.vResizable = true
Slider.hResizable = true
Slider.width = 2


Widgets.register(Slider)
