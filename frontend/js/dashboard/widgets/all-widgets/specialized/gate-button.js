
import $ from '$qui/lib/jquery.module.js'

import {gettext}       from '$qui/base/i18n.js'
import ColorComboField from '$qui/forms/common-fields/color-combo-field.js'
import StockIcon       from '$qui/icons/stock-icon.js'
import * as Theme      from '$qui/theme.js'

import PortPickerField      from '$app/dashboard/widgets/port-picker-field.js'
import Widget               from '$app/dashboard/widgets/widget.js'
import {DEFAULT_COLOR}      from '$app/dashboard/widgets/widget.js'
import WidgetConfigForm     from '$app/dashboard/widgets/widget-config-form.js'
import * as Widgets         from '$app/dashboard/widgets/widgets.js'


const STATE_CLOSING = -2
const STATE_CLOSED = -1
const STATE_STOPPED = 0
const STATE_OPENED = 1
const STATE_OPENING = 2

const STATE_STR = {
    [STATE_CLOSING]: 'closing',
    [STATE_CLOSED]: 'closed',
    [STATE_STOPPED]: 'stopped',
    [STATE_OPENED]: 'opened',
    [STATE_OPENING]: 'opening'
}


/**
 * @class QToggle.DashboardSection.Widgets.GateButton.ConfigForm
 * @extends QToggle.DashboardSection.Widgets.WidgetConfigForm
 * @param {QToggle.DashboardSection.Widgets.Widget} widget
 */
class ConfigForm extends WidgetConfigForm {

    constructor(widget) {
        super(widget, {
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
                    required: true
                })
            ]
        })
    }

}


/**
 * @class QToggle.DashboardSection.Widgets.GateButton
 * @extends QToggle.DashboardSection.Widgets.Widget
 */
class GateButton extends Widget {

    constructor() {
        super()

        this._portState = STATE_STOPPED
        this._color = DEFAULT_COLOR
        this._portId = ''

        this._containerDiv = null
        this._backgroundDiv = null
        this._handleDiv = null
        this._progressDiskDiv = null

        this._vert = false
        this._thickness = 0
        this._handleDiameter = 0
        this._dragIndex = 0
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

        this._portState = value
        this._showState(value)
    }

    makeContent(width, height) {
        if (width > height) {
            this._vert = false
            this._containerDiv = this._makeHorizContent(width, height)
            this._containerDiv.removeClass('vert')
        }
        else {
            this._vert = true
            this._containerDiv = this._makeVertContent(width, height)
            this._containerDiv.addClass('vert')
        }

        /* Update the current state */
        this._showState(this._portState)

        return this._containerDiv
    }

    _makeHorizContent(containerWidth, containerHeight) {
        let left = (containerWidth - 3 * containerHeight) / 2
        let top = 0
        let width = 3 * containerHeight
        let height = containerHeight

        if (containerWidth < 3 * containerHeight) {
            left = 0
            top = (containerHeight - containerWidth / 3) / 2
            width = containerWidth
            height = containerWidth / 3
        }

        let containerDiv = $('<div class="dashboard-gate-button-container"></div>')
        containerDiv.css({
            top: `${top}em`,
            left: `${left}em`,
            width: `${width}em`,
            height: `${height}em`,
            borderWidth: `${Widgets.CELL_PADDING}em`
        })

        this._thickness = height
        this._backgroundDiv = this._makeBackground(this._thickness)
        containerDiv.append(this._backgroundDiv)

        return containerDiv
    }

    _makeVertContent(containerWidth, containerHeight) {
        let left = 0
        let top = (containerHeight - 3 * containerWidth) / 2
        let width = containerWidth
        let height = 3 * containerWidth

        if (containerHeight < 3 * containerWidth) {
            left = (containerWidth - containerHeight / 3) / 2
            top = 0
            height = containerHeight
            width = containerHeight / 3
        }

        let containerDiv = $('<div class="dashboard-gate-button-container"></div>')
        containerDiv.css({
            top: `${top}em`,
            left: `${left}em`,
            width: `${width}em`,
            height: `${height}em`,
            borderWidth: `${Widgets.CELL_PADDING}em`
        })

        this._thickness = width
        this._backgroundDiv = this._makeBackground(this._thickness)
        containerDiv.append(this._backgroundDiv)

        return containerDiv
    }

    _makeBackground(thickness) {
        let backgroundDiv = $('<div class="dashboard-gate-button-background"></div>')

        backgroundDiv.css('border-radius', `${Math.min(this.getContentWidth(), this.getContentHeight())}em`)

        this._handleDiv = this._makeHandle(thickness)
        backgroundDiv.append(this._handleDiv)

        this.setDragElement(backgroundDiv, this._vert ? 'y' : 'x')

        return backgroundDiv
    }

    _makeHandle(thickness) {
        let handleDiv = $('<div class="dashboard-gate-button-handle"></div>')
        let bezelWidth = this.roundEm(Widgets.BEZEL_WIDTH)

        this._handleDiameter = thickness - 2 * (Widgets.CELL_PADDING + bezelWidth)
        handleDiv.css({
            width: `${this._handleDiameter}em`,
            height: `${this._handleDiameter}em`,
            margin: `${bezelWidth}em`,
            color: Theme.getColor(this._color)
        })

        let iconSize = thickness / 2
        let iconScale = this.getEmRatio() / 2 * iconSize
        let iconVariant
        let m = this._color.match('^@([\\w-]+)-color$')
        if (m) {
            iconVariant = m[1]

        }
        else {
            iconVariant = 'foreground'
        }

        let openedIcon = $('<div class="dashboard-gate-button-icon-opened"></div>')
        openedIcon.css({width: `${iconSize}em`, height: `${iconSize}em`})
        new StockIcon({
            stockName: 'qtoggle', name: 'unlock',
            variant: iconVariant, scale: iconScale
        }).applyTo(openedIcon)

        let closedIcon = $('<div class="dashboard-gate-button-icon-closed"></div>')
        closedIcon.css({width: `${iconSize}em`, height: `${iconSize}em`})
        new StockIcon({
            stockName: 'qtoggle', name: 'lock',
            variant: iconVariant, scale: iconScale
        }).applyTo(closedIcon)

        if (this._vert) {
            openedIcon.css('left', `${(this._handleDiameter - iconSize) / 2}em`)
            closedIcon.css('left', `${(this._handleDiameter - iconSize) / 2}em`)
            openedIcon.css('top', `${(-1.8 * thickness)}em`)
            closedIcon.css('bottom', `${(-1.8 * thickness)}em`)
        }
        else {
            openedIcon.css('top', `${(this._handleDiameter - iconSize) / 2}em`)
            closedIcon.css('top', `${(this._handleDiameter - iconSize) / 2}em`)
            openedIcon.css('left', `${(-1.8 * thickness)}em`)
            closedIcon.css('right', `${(-1.8 * thickness)}em`)
        }

        handleDiv.append(openedIcon)
        handleDiv.append(closedIcon)

        this._progressDiskDiv = this._makeProgressDisk()
        handleDiv.append(this._progressDiskDiv)

        return handleDiv
    }

    _makeProgressDisk() {
        let progressDiskDiv = $('<div class="dashboard-gate-button-progress-disk"></div>')
        progressDiskDiv.progressdisk({
            radius: `${(this._handleDiameter / 2)}em`,
            color: this._color
        })
        progressDiskDiv.progressdisk('setValue', -1)

        return progressDiskDiv
    }

    _showState(state) {
        let offset = 0
        let progress = false
        let opened = false
        switch (state) {
            case STATE_CLOSING:
                offset = 0
                progress = true
                opened = false
                break

            case STATE_CLOSED:
                offset = 0
                progress = false
                opened = false
                break

            case STATE_STOPPED:
                offset = 1
                progress = false
                opened = true
                break

            case STATE_OPENED:
                offset = 2
                progress = false
                opened = true
                break

            case STATE_OPENING:
                offset = 2
                progress = true
                opened = true
                break
        }

        /* Adjust class according to new state */
        let classes = Object.values(STATE_STR).map(s => `state-${s}`).join(' ')
        this._containerDiv.removeClass(classes)
        this._containerDiv.addClass(`state-${STATE_STR[state]}`)

        /* Reposition the handle */
        offset *= this._thickness
        if (this._vert) {
            this._handleDiv.css({top: `${offset}em`, left: 0})
        }
        else {
            this._handleDiv.css({left: `${offset}em`, top: 0})
        }

        /* Update progress & color */
        let color
        if (progress) {
            color = 'transparent'
        }
        else if (opened) {
            color = Theme.getColor(this._color)
        }
        else {
            color = ''
        }

        this._handleDiv.toggleClass('progress', progress)
        this._handleDiv.css('background', color)
    }

    _dragIndexFromState() {
        return Math.min(1, Math.max(-1, this._portState))
    }

    onDragBegin() {
        /* Temporarily disable transitions */
        this._handleDiv.css('transition', 'none')

        /* Compute the drag index at the beginning of dragging */
        this._dragIndex = this._dragIndexFromState()
    }

    onDrag(elemX, elemY, deltaX, deltaY) {
        let width = 3 * this._thickness - 2 * Widgets.CELL_PADDING
        let radius = (this._handleDiameter + 2 * Widgets.BEZEL_WIDTH) / 2
        let dragThresh1 = width / 3 - radius
        let dragThresh2 = 2 * width / 3 - radius
        let drag = this._vert ? deltaY : deltaX
        let offset = 0

        let stateDragIndex = this._dragIndexFromState()
        switch (stateDragIndex) {
            case -1:
                drag = Math.max(0, Math.min(2 * this._thickness, drag))
                offset = 0
                break

            case 0:
                drag = Math.max(-this._thickness, Math.min(this._thickness, drag))
                dragThresh1 -= width / 3
                dragThresh2 -= width / 3
                offset = 1
                break

            case 1:
                drag = Math.max(-2 * this._thickness, Math.min(0, drag))
                dragThresh1 -= 2 * width / 3
                dragThresh2 -= 2 * width / 3
                offset = 2
                break
        }

        let dragIndex = drag < dragThresh1 ? -1 : drag < dragThresh2 ? 0 : 1
        if (dragIndex !== this._dragIndex) {
            this.vibrate()
            this._dragIndex = dragIndex
        }

        /* Reposition the handle */
        offset *= this._thickness
        if (this._vert) {
            this._handleDiv.css({top: `${(drag + offset)}em`, left: 0})
        }
        else {
            this._handleDiv.css({left: `${(drag + offset)}em`, top: 0})
        }
    }

    onDragEnd(elemX, elemY, deltaX, deltaY) {
        /* Restore transitions */
        this._handleDiv.css('transition', '')

        let oldDragIndex = this._dragIndexFromState()

        if (oldDragIndex === this._dragIndex) {
            this._showState(this._portState)
            return /* Already there */
        }

        switch (this._dragIndex) {
            case -1:
                this._showState(STATE_CLOSING)

                /* Actually send the new state to the server */
                this.setPortValue(this._portId, STATE_CLOSING)

                break

            case 0:
                this._showState(STATE_STOPPED)

                /* Actually send the new state to the server */
                this.setPortValue(this._portId, STATE_STOPPED)

                break

            case 1:
                this._showState(STATE_OPENING)

                /* Actually send the new state to the server */
                this.setPortValue(this._portId, STATE_OPENING)

                break
        }
    }

    configToJSON() {
        return {
            color: this._color,
            portId: this._portId
        }
    }

    configFromJSON(json) {
        if (json.color) {
            this._color = json.color
        }
        if (json.portId) {
            this._portId = json.portId
        }
    }

    onPortValueChange(portId, value) {
        if (portId !== this._portId) {
            return
        }

        this._portState = value
        this._showState(value)
    }

}

// TODO es7 class fields
GateButton.category = gettext('Specialized')
GateButton.displayName = gettext('Gate Button')
GateButton.typeName = 'GateButton'
GateButton.icon = new StockIcon({name: 'widget', stockName: 'qtoggle'})
GateButton.ConfigForm = ConfigForm
GateButton.hResizable = true
GateButton.vResizable = true


Widgets.register(GateButton)


export default GateButton
