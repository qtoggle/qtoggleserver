
import $      from '$qui/lib/jquery.module.js'
import Logger from '$qui/lib/logger.module.js'

import ConditionVariable    from '$qui/base/condition-variable.js'
import {AssertionError}     from '$qui/base/errors.js'
import {TimeoutError}       from '$qui/base/errors.js'
import {gettext}            from '$qui/base/i18n.js'
import {mix}                from '$qui/base/mixwith.js'
import StockIcon            from '$qui/icons/stock-icon.js'
import {ConfirmMessageForm} from '$qui/messages/common-message-forms.js'
import * as Messages        from '$qui/messages/messages.js'
import * as Toast           from '$qui/messages/toast.js'
import * as Theme           from '$qui/theme.js'
import * as CSS             from '$qui/utils/css.js'
import * as Gestures        from '$qui/utils/gestures.js'
import {asap}               from '$qui/utils/misc.js'
import * as PromiseUtils    from '$qui/utils/promise.js'
import * as StringUtils     from '$qui/utils/string.js'
import ViewMixin            from '$qui/views/view.js'
import * as Window          from '$qui/window.js'

import * as API   from '$app/api.js'
import * as Cache from '$app/cache.js'

import * as Dashboard   from '../dashboard.js'
import WidgetConfigForm from './widget-config-form.js'
import * as Widgets     from './widgets.js'


const DEF_VIBRATION_DURATION = 10 /* Milliseconds */
const PORT_VALUE_CHANGE_TIMEOUT = 3000

const STATES = [
    Widgets.STATE_INVALID,
    Widgets.STATE_NORMAL,
    Widgets.STATE_ERROR,
    Widgets.STATE_PROGRESS
]


/**
 * @class QToggle.DashboardSection.Widgets.Widget
 * @mixes qui.views.ViewMixin
 * @param {Object} attributes
 */
export default class Widget extends mix().with(ViewMixin) {

    constructor() {
        super()

        this._panel = null
        this._bodyDiv = null
        this._labelDiv = null
        this._statusIcon = null
        this._glassDiv = null
        this._contentElem = null
        this._configForm = null

        this._moveControl = null
        this._removeControl = null
        this._configureControl = null
        this._duplicateControl = null
        this._resizeTopControl = null
        this._resizeRightControl = null
        this._resizeBottomControl = null
        this._resizeLeftControl = null

        this._statusIconTimeout = 0

        this._selected = false
        this._px2em = 1
        this._clickDragElemX = null
        this._clickDragElemY = null
        this._dragElem = null

        this._id = null
        this._label = ''
        this._left = 0
        this._top = 0
        this._width = 1
        this._height = 1

        if (this.constructor.width != null) {
            this._width = this.constructor.width
        }
        if (this.constructor.height != null) {
            this._height = this.constructor.height
        }

        this._whenPortValueChanged = null
        this._waitingPortValueChangedId = null

        this.logger = Logger.get(this.makeLogName())
    }


    /* HTML */

    makeHTML() {
        return $('<div class="dashboard-widget-container"></div>')
    }

    initHTML(html) {
        if (this.constructor.hasFrame) {
            html.addClass('has-frame')
        }
        if (this.constructor.protectInvalid) {
            html.addClass('protect-invalid')
        }
        if (this.constructor.protectProgress) {
            html.addClass('protect-progress')
        }

        let bodyDiv = $('<div class="dashboard-widget-body"></div>')
        bodyDiv.css('margin', `${Widgets.CELL_SPACING}em`)
        this._bodyDiv = bodyDiv

        let labelDiv = $('<div class="dashboard-widget-label"><span></span></div>')
        labelDiv.css('height', `${Widgets.LABEL_HEIGHT}em`)
        labelDiv.children('span').css('font-size', `${Widgets.LABEL_FONT_SIZE}em`)

        bodyDiv.append(labelDiv)
        this._labelDiv = labelDiv
        this.setLabel(this._label)

        html.append(bodyDiv)
        html.append(this._makeLayoutControls())

        html.on('pointerdown', function (e) {
            if (!this._panel.isEditEnabled()) {
                return
            }

            /* Select and start moving when clicked, but only in edit mode */
            if (!this.isSelected()) {
                e.stopPropagation()

                this.getPanel().setSelectedWidget(this)
                this.getPanel().handleWidgetSelect(this)
                this._moveControl.trigger(e)

                return false
            }
        }.bind(this))

        this._statusIcon = $('<div class="dashboard-widget-status-icon"></div>')
        html.append(this._statusIcon)

        this._glassDiv = $('<div class="dashboard-widget-glass"></div>')
        html.append(this._glassDiv)

        return html
    }

    /**
     * Override this method to implement the actual content of the widget.
     * @param {Number} width the content (useful) width
     *  (see {@link QToggle.DashboardSection.Widgets.Widget#getContentWidth})
     * @param {Number} height the content (useful) height
     *  (see {@link QToggle.DashboardSection.Widgets.Widget#getContentHeight})
     * @returns {jQuery}
     */
    makeContent(width, height) {
        return $('<span>widget</span>')
    }

    refreshContent() {
        let cw = this.getContentWidth()
        let ch = this.getContentHeight()

        let content = this.makeContent(cw, ch)
        content = content.wrap('<div class="dashboard-widget-content"></div>').parent()
        content.css('height', `${ch}em`)

        if (this._contentElem) {
            this._contentElem.replaceWith(content)
        }
        else {
            this._bodyDiv.append(content)
        }

        this._contentElem = content

        this.showCurrentValue()
    }

    getContentElement() {
        return this._contentElem
    }

    _makeLayoutControls() {
        let controls = $()

        this._moveControl = this._makeMoveControl()
        controls = controls.add(this._moveControl)

        this._removeControl = this._makeRemoveControl()
        controls = controls.add(this._removeControl)

        if (Window.isSmallScreen()) {
            this._configureControl = this._makeConfigureControl()
            controls = controls.add(this._configureControl)
        }

        this._duplicateControl = this._makeDuplicateControl()
        controls = controls.add(this._duplicateControl)

        if (this.constructor.vResizable) {
            this._resizeTopControl = this._makeResizeTopControl()
            this._resizeBottomControl = this._makeResizeBottomControl()

            controls = controls.add(this._resizeTopControl)
                               .add(this._resizeBottomControl)
        }

        if (this.constructor.hResizable) {
            this._resizeRightControl = this._makeResizeRightControl()
            this._resizeLeftControl = this._makeResizeLeftControl()

            controls = controls.add(this._resizeRightControl)
                               .add(this._resizeLeftControl)
        }

        return controls
    }

    _makeMoveControl() {
        let control = $('<div class="dashboard-widget-control dashboard-widget-move"></div>')
        let widget = this
        let changed = false

        function handleMove(elemX, elemY) {
            /* Make the new offsets relative to the panel body */
            let panelBodyOffset = widget._getPanelBody().offset()
            let newOffsetLeft = elemX - panelBodyOffset.left
            let newOffsetTop = elemY - panelBodyOffset.top

            /* Compute the new offsets in em units */
            let cellWidth = widget.getCellWidth()
            let newLeft = Math.round(newOffsetLeft / cellWidth)
            let newTop = Math.round(newOffsetTop / cellWidth)

            /* Limit the new offsets to visible bounding box */
            newLeft = Math.max(0, Math.min(widget._panel.getWidth() - widget._width, newLeft))
            newTop = Math.max(0, Math.min(widget._panel.getHeight() - widget._height, newTop))

            if (!widget._panel.verifyWidgetLayout(newLeft, newTop, widget._width, widget._height, widget)) {
                newLeft = widget._left
                newTop = widget._top
            }

            if (widget._left !== newLeft || widget._top !== newTop) {
                widget._left = newLeft
                widget._top = newTop
                widget.updateLayout()
                changed = true
            }
        }

        Gestures.enableDragging(
            control, handleMove,
            /* onBegin = */ function () {
                changed = false
            },
            /* onEnd = */ function () {
                if (changed) {
                    widget.getPanel().handleWidgetMove(widget)
                }
            },
            /* direction = */ null
        )

        return control
    }

    _makeRemoveControl() {
        let control = $('<div class="qui-base-button dashboard-widget-control dashboard-widget-remove"></div>')
        let iconDiv = $('<div></div>')

        control.append(iconDiv)
        new StockIcon({
            name: 'minus', variant: 'interactive',
            activeVariant: 'interactive brightness(80%)'
        }).applyTo(iconDiv)

        control.on('click', function () {
            this.showConfigForm().then(function () {
                this._configForm.pushPage(this.makeRemoveForm())
            }.bind(this))
        }.bind(this))

        return control
    }

    _makeConfigureControl() {
        let control = $('<div class="qui-base-button dashboard-widget-control dashboard-widget-configure"></div>')
        let widget = this
        let iconDiv = $('<div></div>')

        control.append(iconDiv)

        new StockIcon({
            name: 'wrench', variant: 'interactive',
            activeVariant: 'interactive brightness(80%)'
        }).applyTo(iconDiv)

        control.on('click', function () {
            widget.showConfigForm()
        })

        return control
    }

    _makeDuplicateControl() {
        let control = $('<div class="qui-base-button dashboard-widget-control dashboard-widget-duplicate"></div>')
        let widget = this
        let iconDiv = $('<div></div>')

        control.append(iconDiv)

        new StockIcon({
            name: 'duplicate', variant: 'interactive',
            activeVariant: 'interactive brightness(80%)'
        }).applyTo(iconDiv)

        control.on('click', function () {
            widget.getPanel().duplicateWidget(widget)
        })

        return control
    }

    _makeResizeTopControl() {
        let control = $('<div class="dashboard-widget-control dashboard-widget-resize-control ' +
                        'dashboard-widget-resize-top"></div>')
        let widget = this
        let changed = false

        function handleMove(elemX, elemY, deltaX, deltaY, pageX, pageY) {
            /* Calculate the new offset, in pixels */
            let newOffsetTop = pageY

            /* Make the new offset relative to the panel body */
            let panelBodyOffset = widget._getPanelBody().offset()
            newOffsetTop -= panelBodyOffset.top

            /* Compute the new offset in em units */
            let cellWidth = widget.getCellWidth()
            let newTop = Math.round(newOffsetTop / cellWidth)

            /* Limit the new offset to visible bounding box */
            newTop = Math.max(0, Math.min(widget._top + widget._height - 1, newTop))
            let newHeight = widget._height + widget._top - newTop

            if (!widget._panel.verifyWidgetLayout(widget._left, newTop, widget._width, newHeight, widget)) {
                newTop = widget._top
            }

            if (widget._top !== newTop) {
                widget._height = newHeight
                widget._top = newTop
                widget.updateLayout()
                widget.refreshContent()
                widget.updateState()
                changed = true
            }
        }

        Gestures.enableDragging(control, handleMove, /* onBegin = */ function () {
            changed = false
        }, /* onEnd = */ function () {
            if (changed) {
                widget.getPanel().handleWidgetResize(widget)
            }
        }, /* direction = */ 'y')

        return control
    }

    _makeResizeRightControl() {
        let control = $('<div class="dashboard-widget-control dashboard-widget-resize-control ' +
                        'dashboard-widget-resize-right"></div>')
        let widget = this
        let changed = false

        function handleMove(elemX, elemY, deltaX, deltaY, pageX, pageY) {
            /* Calculate the new offset, in pixels */
            let newOffsetRight = pageX

            /* Make the new offset relative to the panel body */
            let panelBodyOffset = widget._getPanelBody().offset()
            newOffsetRight -= panelBodyOffset.left

            /* Compute the new offset in em units */
            let cellWidth = widget.getCellWidth()
            let newRight = Math.round(newOffsetRight / cellWidth)

            /* Limit the new offset to visible bounding box */
            newRight = Math.max(widget._left + 1, Math.min(widget._panel.getWidth(), newRight))
            let newWidth = newRight - widget._left

            if (!widget._panel.verifyWidgetLayout(widget._left, widget._top, newWidth, widget._height, widget)) {
                newWidth = widget._width
            }

            if (newWidth !== widget._width) {
                widget._width = newWidth
                widget.updateLayout()
                widget.refreshContent()
                widget.updateState()
                changed = true
            }
        }

        Gestures.enableDragging(
            control, handleMove,
            /* onBegin = */ function () {
                changed = false
            },
            /* onEnd = */ function () {
                if (changed) {
                    widget.getPanel().handleWidgetResize(widget)
                }
            },
            /* direction = */ 'x'
        )

        return control
    }

    _makeResizeBottomControl() {
        let control = $('<div class="dashboard-widget-control dashboard-widget-resize-control ' +
                        'dashboard-widget-resize-bottom"></div>')
        let widget = this
        let changed = false

        function handleMove(elemX, elemY, deltaX, deltaY, pageX, pageY) {
            /* Calculate the new offset, in pixels */
            let newOffsetBottom = pageY

            /* Make the new offset relative to the panel body */
            let panelBodyOffset = widget._getPanelBody().offset()
            newOffsetBottom -= panelBodyOffset.top

            /* Compute the new offset in em units */
            let cellWidth = widget.getCellWidth()
            let newBottom = Math.round(newOffsetBottom / cellWidth)

            /* Limit the new offset to visible bounding box */
            newBottom = Math.max(widget._top + 1, Math.min(widget._panel.getHeight(), newBottom))
            let newHeight = newBottom - widget._top

            if (!widget._panel.verifyWidgetLayout(widget._left, widget._top, widget._width, newHeight, widget)) {
                newHeight = widget._height
            }

            if (newHeight !== widget._height) {
                widget._height = newHeight
                widget.updateLayout()
                widget.refreshContent()
                widget.updateState()
                changed = true
            }
        }

        Gestures.enableDragging(
            control, handleMove,
            /* onBegin = */ function () {
                changed = false
            },
            /* onEnd = */ function () {
                if (changed) {
                    widget.getPanel().handleWidgetResize(widget)
                }
            },
            /* direction = */ 'y'
        )

        return control
    }

    _makeResizeLeftControl() {
        let control = $('<div class="dashboard-widget-control dashboard-widget-resize-control ' +
                        'dashboard-widget-resize-left"></div>')
        let widget = this
        let changed = false

        function handleMove(elemX, elemY, deltaX, deltaY, pageX, pageY) {
            /* Calculate the new offset, in pixels */
            let newOffsetLeft = pageX

            /* Make the new offset relative to the panel body */
            let panelBodyOffset = widget._getPanelBody().offset()
            newOffsetLeft -= panelBodyOffset.left

            /* Compute the new offset in em units */
            let cellWidth = widget.getCellWidth()
            let newLeft = Math.round(newOffsetLeft / cellWidth)

            /* Limit the new offset to visible bounding box */
            newLeft = Math.max(0, Math.min(widget._left + widget._width - 1, newLeft))
            let newWidth = widget._width + widget._left - newLeft

            if (!widget._panel.verifyWidgetLayout(newLeft, widget._top, newWidth, widget._height, widget)) {
                newLeft = widget._left
            }

            if (newLeft !== widget._left) {
                widget._width = newWidth
                widget._left = newLeft
                widget.updateLayout()
                widget.refreshContent()
                widget.updateState()
                changed = true
            }
        }

        Gestures.enableDragging(
            control, handleMove,
            /* onBegin = */ function () {
                changed = false
            },
            /* onEnd = */ function () {
                if (changed) {
                    widget.getPanel().handleWidgetResize(widget)
                }
            },
            /* direction = */ 'x'
        )

        return control
    }

    _getPanelBody() {
        return this._panel.getBody()
    }

    getCellWidth() {
        if (!this._panel) {
            return CSS.em2px(1)
        }

        return this._panel.getCellWidth()
    }

    getEmRatio() {
        return this.getCellWidth() / CSS.em2px(1)
    }

    roundEm(em) {
        if (!this._panel) {
            return em
        }

        let cellWidth = this.getCellWidth()

        return Math.round(em * cellWidth) / cellWidth
    }

    getPanel() {
        return this._panel
    }

    getBody() {
        /* Make sure the HTML is created */
        this.getHTML()

        return this._bodyDiv
    }

    updateLayout() {
        this.getHTML().css({
            width: `${this._width}em`,
            height: `${this._height}em`,
            left: `${this._left}em`,
            top: `${this._top}em`
        })
    }


    /* Logging */

    makeLogName() {
        return `qtoggle.dashboard.widgets.widget${this._id || '<new>'}`
    }


    /* Id, label, name */

    /**
     * @returns {?String}
     */
    getId() {
        return this._id
    }

    setId(id) {
        this._id = id
        this.logger = Logger.get(this.makeLogName())
    }

    /**
     * @returns {String}
     */
    getLabel() {
        return this._label
    }

    /**
     * @param {String} label
     */
    setLabel(label) {
        /* Make sure the HTML is created */
        this.getHTML()


        this._label = label
        this._labelDiv.children('span').html(this._label)
        this._labelDiv.css('display', label ? '' : 'none')
        this._bodyDiv.toggleClass('has-label', Boolean(label))

        this.refreshContent()
    }


    /* Size & layout */

    /**
     * @returns {Number}
     */
    getLeft() {
        return this._left
    }

    /**
     * @param {Number} left
     */
    setLeft(left) {
        this._left = left
        this.updateLayout()
        this.refreshContent()
        this.updateState()
    }

    /**
     * @returns {Number}
     */
    getTop() {
        return this._top
    }

    /**
     * @param {Number} top
     */
    setTop(top) {
        this._top = top
        this.updateLayout()
        this.refreshContent()
        this.updateState()
    }

    /**
     * @returns {Number}
     */
    getWidth() {
        return this._width
    }

    /**
     * @param {Number} width
     */
    setWidth(width) {
        this._width = width
        this.updateLayout()
        this.refreshContent()
        this.updateState()
    }

    /**
     * @returns {Number}
     */
    getHeight() {
        return this._height
    }

    /**
     * @param {Number} height
     */
    setHeight(height) {
        this._height = height
        this.updateLayout()
        this.refreshContent()
        this.updateState()
    }

    /**
     * Returns the content (useful) width, in *em* (fractions of a cell).
     * @returns {Number}
     */
    getContentWidth() {
        return this._width - 2 * Widgets.CELL_SPACING
    }

    /**
     * Returns the content (useful) height, in *em* (fractions of a cell).
     * @returns {Number}
     */
    getContentHeight() {
        return this._height - 2 * Widgets.CELL_SPACING - (this._label ? Widgets.LABEL_HEIGHT : 0)
    }


    /* Selection */

    /**
     * @param {Boolean} selected
     */
    setSelected(selected) {
        if (this._selected === selected) {
            return
        }

        this._selected = selected

        if (selected) {
            this.getHTML().addClass('selected')
            asap(function () {
                this.getHTML().addClass('controls-visible')
            }.bind(this))
        }
        else {
            this.getHTML().removeClass('controls-visible')
            Theme.afterTransition(function () {
                this.removeClass('selected')
            }, this.getHTML())
        }
    }

    /**
     * @returns {Boolean}
     */
    isSelected() {
        return this._selected
    }


    /* State */

    /**
     * Recalculates the widget state, updating it accordingly.
     */
    updateState() {
        let computedState = this._computeState()
        let currentState = this.getState()
        if (currentState === computedState) {
            return
        }

        this.setState(computedState)
    }

    enterState(oldState, newState) {
        this.logger.debug(`state ${oldState} -> ${newState}`)

        /* Hide/show protection glass */
        let canEdit = API.getCurrentAccessLevel() >= API.ACCESS_LEVEL_NORMAL
        let wasProtected = (oldState === Widgets.STATE_PROGRESS && this.constructor.protectProgress) ||
                           (oldState === Widgets.STATE_INVALID && this.constructor.protectInvalid)
        let nowProtected = (newState === Widgets.STATE_PROGRESS && this.constructor.protectProgress) ||
                           (newState === Widgets.STATE_INVALID && this.constructor.protectInvalid) || !canEdit

        if (wasProtected && !nowProtected) {
            this._glassDiv.removeClass('visible')
            Theme.afterTransition(function () {
                this.css('display', '')
            }, this._glassDiv)
        }
        else if (!wasProtected && nowProtected) {
            this._glassDiv.css('display', 'block')
            asap(function () {
                this._glassDiv.addClass('visible')
            }.bind(this))
        }

        /* Update state CSS class */
        this.getHTML().removeClass(STATES.join(' ')).addClass(newState)

        /* Update status icon */
        switch (newState) {
            case Widgets.STATE_INVALID:
                this._showStatusIcon(/* visible = */ true, newState)
                break

            case Widgets.STATE_NORMAL:
                this._showStatusIcon(/* visible = */ false, newState)
                break

            default:
                super.enterState(oldState, newState)
        }

        /* Show current value if state transitioned from something bad to valid */
        if ((oldState === Widgets.STATE_INVALID || oldState === Widgets.STATE_ERROR) &&
            (newState === Widgets.STATE_NORMAL)) {

            this.showCurrentValue()
        }
    }

    /**
     * Implement this in concrete widget classes to define in what conditions the widget configuration is valid.
     * By default this method simply returns `true`, which will make the widget's validity rely solely
     * on its configuration form validation.
     * @returns {Boolean}
     */
    isValid() {
        return true
    }

    showProgress(percent) {
        this._showStatusIcon(/* visible = */ true, Widgets.STATE_PROGRESS)
    }

    hideProgress() {
    }

    showError(message) {
        this._showStatusIcon(/* visible = */ true, Widgets.STATE_ERROR)
        // TODO actually display error somehow
    }

    hideError() {
        // TODO remove displayed error
    }

    _computeState() {
        /* Progress has the highest priority */
        if (this.inProgress()) {
            return Widgets.STATE_PROGRESS
        }

        /* Then comes error */
        if (this.hasError()) {
            return Widgets.STATE_ERROR
        }

        if (!this.isValid()) {
            return Widgets.STATE_INVALID
        }

        return Widgets.STATE_NORMAL
    }

    _showStatusIcon(visible, state) {
        if (this._statusIconTimeout) {
            clearTimeout(this._statusIconTimeout)
            this._statusIconTimeout = null
        }

        if (visible) {
            if (!this._statusIcon.hasClass('visible')) {
                this._statusIcon.removeClass('hidden')
                this._statusIcon.removeClass(STATES.join(' ')).addClass(state)
                this._statusIconTimeout = asap(function () {
                    this._statusIconTimeout = null
                    this._statusIcon.addClass('visible')
                }.bind(this))
            }
            else { /* Already visible */
                this._statusIcon.removeClass(STATES.join(' ')).addClass(state)
            }
        }
        else { /* Hide it */
            if (!this._statusIcon.hasClass('hidden')) {
                this._statusIconTimeout = asap(function () {
                    this._statusIcon.removeClass('visible')
                    this._statusIconTimeout = Theme.afterTransition(function () {
                        this._statusIconTimeout = null
                        this._statusIcon.removeClass(STATES.join(' '))
                        this._statusIcon.addClass('hidden')
                    }.bind(this))
                }.bind(this))
            }
        }
    }


    /* Haptic feedback */

    /**
     * Emits a device vibration (if supported).
     * @param {Number} [duration] the vibration duration, in milliseconds. Defaults to `10`.
     */
    vibrate(duration) {
        if (duration == null) {
            duration = DEF_VIBRATION_DURATION
        }

        if (navigator.vibrate) {
            navigator.vibrate(duration)
        }

        this.logger.debug(`vibrate(${duration})`)
    }


    /* Dragging */

    /**
     * Enables dragging on the given element. Only one element at a time can support dragging.
     * @param {jQuery} element
     * @param {String} [direction] indicates dragging direction: `"x"`, `"y"` or `null` for both defaults to `null`
     */
    setDragElement(element, direction) {
        this._clickDragElemX = this._clickDragElemY = null

        if (this._dragElem) {
            Gestures.disableDragging(this._dragElem)
        }

        this._dragElem = element

        if (!element) {
            return
        }

        Gestures.enableDragging(
            element,
            /* onMove = */ function (elemX, elemY, deltaX, deltaY, pageX, pageY) {

                this.onDrag(
                    (this._clickDragElemX + deltaX) * this._px2em,
                    (this._clickDragElemY + deltaY) * this._px2em,
                    deltaX * this._px2em,
                    deltaY * this._px2em
                )

            }.bind(this),
            /* onBegin = */ function (elemX, elemY, pageX, pageY) {

                let elemPosition = this._dragElem.position()

                this._px2em = CSS.px2em(1, this._containerDiv)
                this._clickDragElemX = elemPosition.left
                this._clickDragElemY = elemPosition.top

                this.onDragBegin()

            }.bind(this),
            /* onEnd = */ function (elemX, elemY, deltaX, deltaY, pageX, pageY) {

                this.onDragEnd(
                    (this._clickDragElemX + deltaX) * this._px2em,
                    (this._clickDragElemY + deltaY) * this._px2em,
                    deltaX * this._px2em,
                    deltaY * this._px2em
                )

                this._clickDragElemX = this._clickDragElemY = null

            }.bind(this),
            direction
        )
    }

    /**
     * Called when the dragging begins.
     */
    onDragBegin() {
    }

    /**
     * Called during dragging with drag offsets.
     * @param {Number} elemX the new element x coordinate, relative to its offset parent
     * @param {Number} elemY the new element y coordinate, relative to its offset parent
     * @param {Number} deltaX the x coordinate variation, relative to initial drag point
     * @param {Number} deltaY the y coordinate variation, relative to initial drag point
     */
    onDrag(elemX, elemY, deltaX, deltaY) {
    }

    /**
     * Called when the drag ends, with final drag offsets.
     * @param {Number} elemX the new element x coordinate, relative to its offset parent
     * @param {Number} elemY the new element y coordinate, relative to its offset parent
     * @param {Number} deltaX the x coordinate variation, relative to initial drag point
     * @param {Number} deltaY the y coordinate variation, relative to initial drag point
     */
    onDragEnd(elemX, elemY, deltaX, deltaY) {
    }

    /**
     * Tells if the drag element is currently being dragged.
     * @returns {Boolean}
     */
    isDragging() {
        return Boolean(this._dragElem) && this._clickDragElemX != null
    }


    /* Serialization */

    /**
     * @returns {Object}
     */
    toJSON() {
        let json = {
            id: this._id,
            label: this._label,
            left: this._left,
            top: this._top,
            config: this.configToJSON()
        }

        if (this.constructor.hResizable) {
            json.width = this._width
        }
        if (this.constructor.vResizable) {
            json.height = this._height
        }

        return json
    }

    /**
     * @param {Object} json
     */
    fromJSON(json) {
        if (json.id != null) {
            this._id = json.id
        }
        if (json.label != null) {
            this.setLabel(json.label)
        }
        if (json.left != null) {
            this._left = json.left
        }
        if (json.top != null) {
            this._top = json.top
        }
        if (this.constructor.hResizable) {
            if (json.width != null) {
                this._width = json.width
            }
        }
        if (this.constructor.vResizable) {
            if (json.height != null) {
                this._height = json.height
            }
        }
        if (json.config) {
            this.configFromJSON(json.config)
        }

        this.logger = Logger.get(this.makeLogName())
    }

    /**
     * @returns {Object}
     */
    configToJSON() {
        return {}
    }

    /**
     * @param {Object} json
     */
    configFromJSON(json) {
    }


    /* Values */

    setWaitingPortValueChanged(portId) {
        if (this._whenPortValueChanged) {
            throw new AssertionError('Attempt to wait for value change while already waiting')
        }

        this._whenPortValueChanged = new ConditionVariable()
        this._waitingPortValueChangedId = portId

        PromiseUtils.withTimeout(this._whenPortValueChanged, PORT_VALUE_CHANGE_TIMEOUT).catch(function (error) {

            if (error instanceof TimeoutError) {
                this.logger.debug(`value-change not received within timeout for ${portId}, reverting to current one`)
                let port = Cache.getPort(portId)
                if (!port) {
                    return
                }

                this.onPortValueChange(portId, port.value)
            }

            /* Other errors can practically only be generated by cancelling the condition variable */

        }.bind(this))
    }

    clearWaitingPortValueChanged() {
        if (!this._whenPortValueChanged) {
            throw new AssertionError('Attempt to cancel waiting for value change while not waiting')
        }

        this._whenPortValueChanged.cancel()
        this._whenPortValueChanged = null
        this._waitingPortValueChangedId = null
    }

    isWaitingPortValueChanged() {
        return !!this._whenPortValueChanged
    }

    handlePortValueChange(portId, value) {
        if (this._waitingPortValueChangedId === portId) {
            this.clearWaitingPortValueChanged()
        }

        this.onPortValueChange(portId, value)
    }

    /**
     * Override this to implement widget-specific reaction to the change of a port value.
     * @param {String} portId the id of the port whose value has changed
     * @param {Number|Boolean} value the new port value
     */
    onPortValueChange(portId, value) {
    }

    /**
     * Sets the value of a port. This is basically a handy wrapper around {@link QToggle.API.patchPortValue}.
     * During the API call, the widget is put into *progress* state.
     * When the call returns, the state is updated according to the result.
     * @param {String} portId the id of the port whose value will be set
     * @param {Number|Boolean} value the new port value
     * @returns {Promise}
     */
    setPortValue(portId, value) {
        this.setProgress()

        return API.patchPortValue(portId, value).then(function () {

            this.clearProgress()

            if (this.isWaitingPortValueChanged()) {
                this.clearWaitingPortValueChanged(portId)
            }

            this.setWaitingPortValueChanged(portId)

        }.bind(this)).catch(function (error) {

            this.setError(error)
            this.showCurrentValue() /* This will normally revert to previous value */

            Toast.error(error.message)

        }.bind(this))
    }

    /**
     * Returns the cached value of a port.
     * @param {String} portId the id of the port whose value will be returned
     * @returns {?Boolean|Number}
     */
    getPortValue(portId) {
        let port = Cache.getPort(portId)
        if (!port) {
            return null
        }

        return port.value
    }

    /**
     * Sets the value of a port. This is basically a handy wrapper around {@link QToggle.API.postPortSequence}.
     * During the API call, the widget is put into *progress* state.
     * When the call returns, the state is updated according to the result.
     * @param {String} portId the id of the port whose value will be set
     * @param {Boolean[]|Number[]} values the list of values in the sequence
     * @param {Number[]} delays the list of delays between values
     * @param {Number} repeat how many times to repeat the sequence
     * @returns {Promise}
     */
    setPortSequence(portId, values, delays, repeat) {
        this.setProgress()

        return API.postPortSequence(portId, values, delays, repeat).then(function () {

            this.clearProgress()

        }.bind(this)).catch(function (error) {

            this.setError(error)
            this.showCurrentValue() /* This will normally revert to previous value */

            Toast.error(error.message)

        }.bind(this))
    }

    /**
     * Returns the cached attributes of a port.
     * @param {String} portId the id of the port whose attributes will be returned
     * @returns {?Object}
     */
    getPort(portId) {
        return Cache.getPort(portId)
    }

    /**
     * Returns the device attached to the given port.
     * @param {String} portId the id of the port
     * @returns {?Object}
     */
    getPortDevice(portId) {
        return Cache.findPortSlaveDevice(portId)
    }

    /**
     * Override this method to implement updating the widget (usually from port values)
     * as soon as the widget becomes valid.
     */
    showCurrentValue() {
    }


    /* Configuration */

    makeRemoveForm() {
        let msg
        if (this._label) {
            msg = StringUtils.formatPercent(
                gettext('Really remove %(object)s?'),
                {object: Messages.wrapLabel(this._label)}
            )
        }
        else {
            msg = gettext('Really remove this widget?')
        }

        return new ConfirmMessageForm({
            message: msg,
            onYes: function () {
                this.logger.debug('removing')
                this._panel.removeWidget(this)
                Dashboard.savePanels()
                this._configForm.close(/* force = */ true)
            }.bind(this),
            pathId: 'remove'
        })
    }

    /**
     * @returns {QToggle.DashboardSection.Widgets.WidgetConfigForm}
     */
    getConfigForm() {
        if (!this._configForm) {
            this._configForm = new this.constructor.ConfigForm(this)
        }

        this._configForm.updateFromWidget()

        return this._configForm
    }

    showConfigForm() {
        let configForm = this.getConfigForm()
        if (configForm.hasContext()) { /* Already added */
            return Promise.resolve()
        }

        return this._panel.pushPage(this.getConfigForm())
    }

}

// TODO es7 class fields
Widget.category = ''
Widget.displayName = ''
Widget.icon = null
Widget.typeName = 'Widget'
Widget.ConfigForm = WidgetConfigForm

Widget.protectProgress = false /* Prevent user interaction when widget is in progress */
Widget.protectInvalid = true /* Prevent user interaction when widget is invalid */
Widget.width = null
Widget.height = null
Widget.vResizable = false
Widget.hResizable = false
Widget.hasFrame = false
