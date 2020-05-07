
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

import PortPickerField  from '$app/dashboard/widgets/port-picker-field.js'
import Widget           from '$app/dashboard/widgets/widget.js'
import {DEFAULT_COLOR}  from '$app/dashboard/widgets/widget.js'
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


/**
 * @alias qtoggle.dashboard.widgets.AnalogWidgetConfigForm
 * @extends qtoggle.dashboard.widgets.ConfigForm
 */
export class ConfigForm extends WidgetConfigForm {

    /**
     * @constructs
     * @param {Boolean} [readonly]
     * @param {Boolean} [ticksonly]
     * @param {Boolean} [tickColors]
     * @param {...*} args
     */
    constructor({readonly = false, ticksonly = false, tickColors = false, ...args}) {
        super({
            fields: [
                new PortPickerField({
                    name: 'portId',
                    label: gettext('Port'),
                    required: true
                }),
                new NumericField({
                    name: 'min',
                    label: gettext('Min Value'),
                    required: true,
                    hidden: ticksonly
                }),
                new NumericField({
                    name: 'max',
                    label: gettext('Max Value'),
                    required: true,
                    hidden: ticksonly
                }),
                new ColorComboField({
                    name: 'minColor',
                    label: gettext('Min Color'),
                    filterEnabled: true,
                    required: true,
                    hidden: ticksonly
                }),
                new ColorComboField({
                    name: 'maxColor',
                    label: gettext('Max Color'),
                    filterEnabled: true,
                    required: true,
                    hidden: ticksonly
                }),
                new CheckField({
                    name: 'negativeProgress',
                    label: gettext('Negative Values Progress'),
                    description: gettext('The negatives of defined values will be shown as widget progress'),
                    hidden: !ticksonly
                }),
                new CheckField({
                    name: 'displayValue',
                    label: gettext('Display Value'),
                    separator: true,
                    onChange: (value, form) => form._updateFields()
                }),
                new CheckField({
                    name: 'displayUnit',
                    label: gettext('Display Unit'),
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
                    ],
                    hidden: ticksonly || readonly
                }),
                new CheckField({
                    name: 'displayTicks',
                    label: gettext('Display Ticks'),
                    separator: ticksonly || readonly,
                    onChange: (value, form) => form._updateFields()
                }),
                new CheckField({
                    name: 'displayTicksUnits',
                    label: gettext('Display Ticks Units'),
                    onChange: (value, form) => form._updateFields()
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
                    onChange: (value, form) => form._updateFields()
                }),
                new CheckField({
                    name: 'customTicks',
                    label: gettext('Custom Ticks'),
                    onChange: (value, form) => form._updateFields(),
                    hidden: ticksonly
                })
            ],
            ...args
        })

        this._readonly = readonly
        this._ticksonly = ticksonly
        this._tickColors = tickColors
    }

    onUpdateFromWidget() {
        this._updateFields()
    }

    _updateFields() {
        let data = this.getUnvalidatedData()
        let port = this.getPort(data.portId)

        /* Gather current custom ticks fields */
        let customTicksValueFields = this.getFields().filter(f => f.getName().match(new RegExp('tickValue\\d+')))
        let customTicksLabelFields = this.getFields().filter(f => f.getName().match(new RegExp('tickLabel\\d+')))
        let customTicksColorFields = this.getFields().filter(f => f.getName().match(new RegExp('tickColor\\d+')))

        /* Add new needed fields */
        let lastTickFieldNo = customTicksLabelFields.length - 1
        ArrayUtils.range(lastTickFieldNo + 1, data.ticksCount).forEach(function (no) {

            let fields = this._addTickFields(no, port)

            customTicksValueFields.push(fields.valueField)
            customTicksLabelFields.push(fields.labelField)
            if (this._tickColors) {
                customTicksColorFields.push(fields.colorField)
            }

        }.bind(this))

        let customTicksFields = [...customTicksValueFields, ...customTicksLabelFields, ...customTicksColorFields]
        let customTicksFieldNames = customTicksFields.map(f => f.getName())

        let visibleFieldNames = {}
        let allFieldNames = [
            'unit',
            'displayUnit',
            'displayTicksUnits',
            'decimals',
            'ticksCount',
            'customTicks',
            'ticksStep',
            'colorTicks',
            ...customTicksFieldNames
        ]

        /* An analog widget has ticks if it's editable, if user wants ticks to be displayed or has ticksonly flag */
        let hasTicks = data.displayTicks || !this._readonly || this._ticksonly

        /* Analog widgets with ticksonly flag always have custom ticks */
        let hasCustomTicks = data.customTicks || this._ticksonly

        if (data.displayTicks) {
            visibleFieldNames['colorTicks'] = true
            if (!hasCustomTicks) {
                visibleFieldNames['displayTicksUnits'] = true
            }
            if (!this._ticksonly) {
                visibleFieldNames['ticksStep'] = true
            }
        }

        if (hasTicks) {
            visibleFieldNames['ticksCount'] = true
            if (!this._ticksonly) {
                visibleFieldNames['customTicks'] = true
            }
        }

        if (data.displayValue && !hasCustomTicks) {
            visibleFieldNames['displayUnit'] = true
            visibleFieldNames['decimals'] = true
            if (data.displayUnit) {
                visibleFieldNames['unit'] = true
            }
        }

        if (data.displayTicks && !hasCustomTicks) {
            visibleFieldNames['decimals'] = true
            if (data.displayTicksUnits) {
                visibleFieldNames['unit'] = true
            }
        }

        if (hasTicks && hasCustomTicks) {
            /* Show all used custom ticks fields */
            ArrayUtils.range(0, data.ticksCount).forEach(function (no) {

                let fields = this._getTickFields(no)

                visibleFieldNames[fields.valueField.getName()] = true
                visibleFieldNames[fields.labelField.getName()] = true
                if (this._tickColors) {
                    visibleFieldNames[fields.colorField.getName()] = true
                }

            }.bind(this))
        }

        /* Actually update fields visibility */
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

        let customTicksField = this.getField('customTicks')
        let index = this.getFieldIndex(customTicksField) + 1 + no * (this._tickColors ? 3 : 2)

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
        this.addField(index, valueField)

        let labelField = new TextField({
            name: `tickLabel${no}`,
            label: `${gettext('Tick Label')} ${no + 1}`
        })
        this.addField(index + 1, labelField)

        let colorField
        if (this._tickColors) {
            colorField = new ColorComboField({
                name: `tickColor${no}`,
                label: `${gettext('Tick Color')} ${no + 1}`,
                filterEnabled: true,
                required: true
            })
            this.addField(index + 2, colorField)
        }

        return {
            valueField: valueField,
            labelField: labelField,
            colorField: colorField
        }
    }

    _getTickFields(no) {
        let valueField = this.getField(`tickValue${no}`)
        let labelField = this.getField(`tickLabel${no}`)
        let colorField = this.getField(`tickColor${no}`)

        return {
            valueField: valueField,
            labelField: labelField,
            colorField: colorField
        }
    }

    fromWidget(widget) {
        let data = super.fromWidget(widget)

        data.customTicks.forEach(function (t, no) {
            data[`tickValue${no}`] = t.value
            data[`tickLabel${no}`] = t.label
            if (this._tickColors) {
                data[`tickColor${no}`] = t.color
            }
        }.bind(this))

        data.customTicks = Boolean(data.customTicks.length) || this._ticksonly

        return data
    }

    toWidget(data, widget) {
        if (data.customTicks) {
            data.customTicks = ArrayUtils.range(0, data.ticksCount).map(function (no) {

                let d = {
                    value: data[`tickValue${no}`],
                    label: data[`tickLabel${no}`]
                }

                if (this._tickColors) {
                    d['color'] = data[`tickColor${no}`]
                }

                return d

            }.bind(this))
        }
        else {
            data.customTicks = []
        }

        super.toWidget(data, widget)
    }

    fromPort(port, fieldName) {
        let data = super.fromPort(port, fieldName)

        data.unit = port.unit
        data.min = port.min != null ? port.min : 0
        data.max = port.max != null ? port.max : 100

        return data
    }

}


/**
 * @alias qtoggle.dashboard.widgets.AnalogWidget
 * @extends qtoggle.dashboard.widgets.Widget
 */
export class AnalogWidget extends Widget {

    /**
     * @constructs
     * @param {Boolean} [readonly]
     * @param {Boolean} [ticksonly]
     * @param {Boolean} [tickColors]
     */
    constructor({readonly = false, ticksonly = false, tickColors = false} = {}) {
        super()

        this._portId = ''
        this._min = 0
        this._max = 100
        this._minColor = '@gray-color'
        this._maxColor = DEFAULT_COLOR
        this._negativeProgress = false
        this._displayValue = true
        this._displayUnit = true
        this._unit = ''
        this._decimals = 0
        this._snap = SNAP_NONE
        this._displayTicks = false
        this._displayTicksUnits = false
        this._colorTicks = false
        this._ticksStep = 1
        this._ticksCount = 0
        this._customTicks = []
        this._readonly = readonly
        this._ticksonly = ticksonly
        this._tickColors = tickColors

        this._containerDiv = null
        this._backgroundDiv = null
        this._backgroundCoverDiv = null
        this._ticksDiv = null
        this._cursorDiv = null
        this._handleDiv = null
        this._progressDiskDiv = null
        this._textDiv = null

        this._thickness = 0
        this._length = 0
        this._bezelWidth = 0
        this._handleDiameter = 0

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
        /* Bezel width must be recomputed here so that we get the proper rounded value */
        this._bezelWidth = this._ticksonly ? 0 : this.roundEm(Widgets.BEZEL_WIDTH)

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
                String(this._min.toFixed(this._decimals) + unit).length,
                String(this._min.toFixed(this._decimals) + unit).length
            )

            this._ticksThicknessFactor *= (1 + 1.5 * (len - 2) / 10)
        }

        if (this._displayTicks) {
            this._thickness *= (1 - this._ticksThicknessFactor)
        }
        this._ticksDiv = this._makeTicks() /* This must be here, as it uses this._thickness internally */
        if (this._displayTicks) {
            this._containerDiv.append(this._ticksDiv)
        }

        this._backgroundDiv = this._makeBackground()
        this._containerDiv.append(this._backgroundDiv)

        this._backgroundCoverDiv = this._makeBackgroundCover()
        this._backgroundDiv.append(this._backgroundCoverDiv)

        if (this._readonly) {
            this._cursorDiv = this._makeCursor()
            this._backgroundDiv.append(this._cursorDiv)
        }
        else {
            this._handleDiv = this._makeHandle()
            this._backgroundDiv.append(this._handleDiv)
            this.setDragElement(this._backgroundDiv, this._vert ? 'y' : 'x')

            if (this._negativeProgress) {
                this._progressDiskDiv = this._makeProgressDisk()
                this._handleDiv.append(this._progressDiskDiv)
            }
        }

        if (this._displayValue) {
            this._textDiv = this._makeText()
            this._backgroundDiv.append(this._textDiv)
        }

        /* Set an initial state */
        this._showValue(this._min)

        return this._containerDiv
    }

    _makeBackground() {
        let backgroundThickness = this._thickness - 2 * Widgets.CELL_PADDING

        let backgroundDiv = $(`<div class="dashboard-analog-widget-background
                                           dashboard-${this._widgetName}-background"></div>`)

        backgroundDiv.css('border-radius', `${Math.min(this.getContentWidth(), this.getContentHeight())}em`)
        backgroundDiv.css(this._vert ? 'width' : 'height', `${backgroundThickness}em`)
        backgroundDiv.css('border-width', `${this._bezelWidth}em`)

        /* When ticksonly flag is set, we only want one button and no color on background */
        if (!this._ticksonly) {
            let startColor = this._valueToColor(this._min)
            let endColor = this._valueToColor(this._max)
            let direction = this._vert ? 'to top' : 'to right'
            let backgroundGradient = `linear-gradient(${direction}, ${startColor}, ${endColor})`
            backgroundDiv.css('background', backgroundGradient)
        }

        return backgroundDiv
    }

    _makeBackgroundCover() {
        let backgroundCoverDiv = $(`<div class="dashboard-analog-widget-background-cover
                                                dashboard-${this._widgetName}-background-cover"></div>`)
        backgroundCoverDiv.css('margin', `${this._bezelWidth}em`)

        return backgroundCoverDiv
    }

    _makeCursor() {
        let height = (this._thickness - 2 * (Widgets.CELL_PADDING + this._bezelWidth))
        let cursorDiv = $(`<div class="dashboard-analog-widget-cursor
                                       dashboard-${this._widgetName}-cursor"></div>`)

        cursorDiv.css({
            left: `${this._bezelWidth}em`,
            height: `${height}em`
        })

        return cursorDiv
    }

    _makeHandle() {
        this._handleDiameter = this._thickness - 2 * Widgets.CELL_PADDING - 4 * this._bezelWidth
        let handleDiv = $(`<div class="qui-base-button dashboard-analog-widget-handle
                                       dashboard-${this._widgetName}-handle"></div>`)

        handleDiv.css({
            'width': `${this._handleDiameter}em`,
            'height': `${this._handleDiameter}em`,
            'margin': `${this._bezelWidth}em`,
            'border-width': `${this.roundEm(Widgets.BEZEL_WIDTH)}em`
        })

        return handleDiv
    }

    _makeProgressDisk() {
        let radius = this._handleDiameter / 2 - this.roundEm(Widgets.BEZEL_WIDTH)
        let progressDiskDiv = $(`<div class="dashboard-analog-widget-progress-disk
                                             dashboard-${this._widgetName}-progress-disk"></div>`)
        progressDiskDiv.progressdisk({
            radius: `${radius}em`
        })
        progressDiskDiv.progressdisk('setValue', -1)

        return progressDiskDiv
    }

    _makeText() {
        let fontSize = TEXT_FACTOR * this._thickness
        let textDiv = $(`<div class="dashboard-analog-widget-text dashboard-${this._widgetName}-text"></div>`)

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
            let label, value, step = (this._max - this._min) / (this._ticksCount - 1)
            for (let i = 0; i < this._ticksCount; i++) {
                if (i < this._ticksCount - 1) {
                    value = this._min + i * step
                }
                else {
                    value = this._max
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
            let factor
            if (this._ticksonly) {
                /* Make ticks equidistant if using ticksonly */
                factor = i / (this._ticks.length - 1)
            }
            else {
                factor = this._valueToFactor(tick.value) /* Yes, factor */
            }

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
                if (tick.color) {
                    labelDiv.css('color', Theme.getColor(tick.color))
                }
                else {
                    labelDiv.css('color', this._valueToColor(tick.value))
                }
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

        }.bind(this))

        return ticksDiv
    }

    _showValue(value, pos = null) {
        let showProgress = false
        if (this._negativeProgress && value < 0) {
            value = -value
            showProgress = true
        }

        if (this._min < this._max) {
            value = Math.min(Math.max(value, this._min), this._max)
        }
        else {
            value = Math.min(Math.max(value, this._max), this._min)
        }

        /* Position */
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

        if (factor === 1 && this._readonly) {
            /* Ensure the cursor actually covers the entire area, eliminating rounding problems */
            pos = '100%'
        }
        else {
            pos = `${pos}em`
        }

        this._containerDiv.toggleClass('end-half', factor > 0.5)

        /* Color */
        let color
        if (this._tickColors && tick && tick.color) {
            color = Theme.getColor(tick.color)
        }
        else {
            color = this._valueToColor(value)
        }

        if (this._cursorDiv) {
            let startColor = this._valueToColor(this._min)
            let direction = this._vert ? 'to top' : 'to right'
            let backgroundGradient = `linear-gradient(${direction}, ${startColor}, ${color})`
            this._cursorDiv.css('background', backgroundGradient)
        }

        if (this._handleDiv) {
            if (showProgress) {
                this._progressDiskDiv.progressdisk({color: color})
                color = 'transparent'
            }

            this._handleDiv.toggleClass('progress', showProgress)
            this._handleDiv.css('background', color)
        }

        if (this._vert) {
            if (this._cursorDiv) {
                this._cursorDiv.css('height', pos)
            }
            if (this._handleDiv) {
                this._handleDiv.css('bottom', pos)
            }
            if (!this._readonly) {
                this._backgroundCoverDiv.css('bottom', pos)
            }
        }
        else {
            if (this._cursorDiv) {
                this._cursorDiv.css('width', pos)
            }
            if (this._handleDiv) {
                this._handleDiv.css('left', pos)
            }
            if (!this._readonly) {
                this._backgroundCoverDiv.css('left', pos)
            }
        }

        if (this._textDiv) {
            let valueStr
            if (tick && this._customTicks.length) {
                valueStr = tick.label
            }
            else {
                valueStr = value.toFixed(this._decimals)
                if (this._displayUnit) {
                    valueStr += this._unit
                }
            }

            this._textDiv.html(valueStr)

            let fontSize = TEXT_FACTOR * this._thickness
            factor = 1 - factor
            let offs = factor > 0.5 ? factor : (1 - factor)
            let length = (this._getUsefulLength() * offs) / fontSize

            this._textDiv.css(this._vert ? 'height' : 'width', `${length}em`)

            let foregroundColor = Theme.getColor('@foreground-color')
            let backgroundColor = Theme.getColor('@background-color')

            let foregroundRGB = Colors.str2rgba(foregroundColor)
            let colorRGB = Colors.str2rgba(color)

            this._textDiv.css('color', foregroundColor)

            if (this._containerDiv.hasClass('end-half')) {
                if (Colors.contrast(foregroundRGB, colorRGB) < 1.5 && !this._ticksonly) {
                    this._textDiv.css('color', backgroundColor)
                }
            }
        }
    }

    _valueToFactor(value) {
        return (value - this._min) / (this._max - this._min)
    }

    _factorToValue(factor) {
        return this._min + factor * (this._max - this._min)
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
        return Colors.mix(Theme.getColor(this._minColor), Theme.getColor(this._maxColor), this._valueToFactor(value))
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
        else {
            /* Round to displayed number of decimals */
            let pow10 = Math.pow(10, this._decimals)
            value = Math.round(pow10 * value) / pow10
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
            min: this._min,
            max: this._max,
            minColor: this._minColor,
            maxColor: this._maxColor,
            negativeProgress: this._negativeProgress,
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
        if (json.min != null) {
            this._min = json.min
        }
        if (json.max != null) {
            this._max = json.max
        }
        if (json.minColor) {
            this._minColor = json.minColor
        }
        if (json.maxColor) {
            this._maxColor = json.maxColor
        }
        if (json.negativeProgress != null) {
            this._negativeProgress = json.negativeProgress
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

        if (this._ticksonly) {
            this._min = Math.min.apply(null, this._customTicks.map(t => t.value))
            this._max = Math.max.apply(null, this._customTicks.map(t => t.value))
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
