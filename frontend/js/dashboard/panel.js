
import $      from '$qui/lib/jquery.module.js'
import Logger from '$qui/lib/logger.module.js'

import {gettext}             from '$qui/base/i18n.js'
import {mix}                 from '$qui/base/mixwith.js'
import {CheckField}          from '$qui/forms/common-fields.js'
import {PushButtonField}     from '$qui/forms/common-fields.js'
import {TextField}           from '$qui/forms/common-fields.js'
import {UpDownField}         from '$qui/forms/common-fields.js'
import {OptionsForm}         from '$qui/forms/common-forms.js'
import FormButton            from '$qui/forms/form-button.js'
import {ValidationError}     from '$qui/forms/forms.js'
import * as OptionsBar       from '$qui/main-ui/options-bar.js'
import {StructuredPageMixin} from '$qui/pages/common-pages.js'
import * as Theme            from '$qui/theme.js'
import * as ArrayUtils       from '$qui/utils/array.js'
import * as Crypto           from '$qui/utils/crypto.js'
import * as CSS              from '$qui/utils/css.js'
import {asap}                from '$qui/utils/misc.js'
import * as ObjectUtils      from '$qui/utils/object.js'
import * as Window           from '$qui/window.js'

import * as API from '$app/api.js'

import * as Dashboard           from './dashboard.js'
import PanelGroupCompositeMixin from './panel-group-composite.js'
import WidgetPicker             from './widgets/widget-picker.js'
import * as Widgets             from './widgets/widgets.js'


const DEFAULT_PANEL_WIDTH = 5
const DEFAULT_PANEL_HEIGHT = 5

const MAX_PANEL_WIDTH = 20
const MAX_PANEL_HEIGHT = 100


class PanelOptionsForm extends OptionsForm {

    constructor(panel) {
        super({
            page: panel,
            buttons: [
                new FormButton({id: 'remove', caption: gettext('Remove'), style: 'danger'})
            ],
            fields: [
                new TextField({
                    name: 'name',
                    label: gettext('Name'),
                    required: true,
                    maxLength: 64
                }),
                new UpDownField({
                    name: 'width',
                    label: gettext('Width'),
                    required: true,
                    min: 1,
                    max: MAX_PANEL_WIDTH
                }),
                new UpDownField({
                    name: 'height',
                    label: gettext('Height'),
                    required: true,
                    min: 1,
                    max: MAX_PANEL_HEIGHT
                }),
                new CheckField({
                    name: 'optimizeSmallScreen',
                    label: gettext('Mobile View')
                }),
                new PushButtonField({
                    name: 'addWidgetButton',
                    caption: gettext('Add Widget'),
                    style: 'highlight',
                    valueWidth: 100,
                    hidden: true,
                    onClick(form) {
                        let panel = form._panel
                        panel.pushPage(panel.makeWidgetPicker())
                    }
                })
            ],
            data: {
                name: panel.getName(),
                width: panel.getWidth(),
                height: panel.getHeight(),
                optimizeSmallScreen: panel.isOptimizeSmallScreen()
            },
            continuousValidation: true
        })

        this._panel = panel
    }

    init() {
        this._updateEditState()
        this.updateSizeLimits()
    }

    _updateEditState() {
        let editButton = this._getEditButton()
        let addWidgetButton = this.getField('addWidgetButton')
        let widthField = this.getField('width')
        let heightField = this.getField('height')

        if (this._panel.isEditEnabled()) {
            editButton.setCaption(gettext('Done'))
            addWidgetButton.show()
            widthField.show()
            heightField.show()
        }
        else {
            editButton.setCaption(gettext('Edit'))
            addWidgetButton.hide()
            widthField.hide()
            heightField.hide()
        }
    }

    _getEditButton() {
        let button = this.getButton('edit')
        if (!button) {
            button = new FormButton({
                id: 'edit',
                caption: '',
                style: 'interactive'
            })
            this.addButton(0, button)
        }

        return button
    }

    updateSizeLimits() {
        let maxX = -1
        let maxY = -1

        this._panel.getWidgets().forEach(function (w) {
            let x = w.getLeft() + w.getWidth() - 1
            let y = w.getTop() + w.getHeight() - 1

            if (x > maxX) {
                maxX = x
            }
            if (y > maxY) {
                maxY = y
            }
        })

        this.getField('width').setMin(maxX + 1)
        this.getField('height').setMin(maxY + 1)
    }

    validateField(name, value, data) {
        switch (name) {
            case 'name': {
                let child = this._panel.getParent().findChildByName(value)
                if (child && child !== this._panel) {
                    throw new ValidationError(gettext('This name already exists!'))
                }
            }
        }
    }

    onButtonPress(button) {
        switch (button.getId()) {
            case 'remove':
                this._panel.pushPage(this._panel.makeRemoveForm())

                break

            case 'edit': {
                if (this._panel.isEditEnabled()) {
                    this._panel.disableEditing()
                }
                else {
                    this._panel.enableEditing()
                }

                this._updateEditState()
                this._panel.updateHistoryState()

                break
            }
        }
    }

    onOptionsBarOpenClose(opened) {
        this._updateEditState()
    }

}


/**
 * @alias qtoggle.dashboard.Panel
 * @mixes qtoggle.dashboard.PanelGroupCompositeMixin
 * @mixes qui.pages.StructuredPageMixin
 */
class Panel extends mix().with(PanelGroupCompositeMixin, StructuredPageMixin) {

    /**
     * @constructs
     * @param {...*} args
     */
    constructor({...args} = {}) {
        Object.assign(args, {
            pathId: '',
            transparent: true,
            title: '',
            icon: Dashboard.PANEL_ICON,
            keepPrevVisible: false,
            topless: true
        })

        super(args)

        this._optionsForm = null

        this._optimizeSmallScreen = false
        this._editEnabled = false
        this._cellWidth = null
        this._widgets = null
        this._widgetsJSON = null
        this._width = DEFAULT_PANEL_WIDTH
        this._height = DEFAULT_PANEL_HEIGHT

        this.logger = Logger.get(this.makeLogName())
    }

    init() {
        this.updateUI()
    }


    /* HTML */

    makeHTML() {
        return $('<div class="dashboard-panel"></div>')
    }

    makeBody() {
        return $('<div class="panel-container"></div>')
    }


    /* Logging */

    makeLogName() {
        return `qtoggle.dashboard.panels.panel-${this.getId()}`
    }


    /* Size & layout */

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
        this.updateUI()
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
        this.updateUI()
    }

    /**
     * Tell if a given layout for the given widget fits the current panel layout and has no overlapping widgets.
     * @param {Number} left
     * @param {Number} top
     * @param {Number} width
     * @param {Number} height
     * @param {qtoggle.dashboard.widgets.Widget} [widget]
     * @returns {Boolean}
     */
    verifyWidgetLayout(left, top, width, height, widget) {
        /* Verify panel boundaries */
        if (left < 0 || top < 0) {
            return false
        }

        if (left + width > this._width || top + height > this._height) {
            return false
        }

        /* Verify overlapping widgets */
        return !this.getWidgets().some(function (w) {

            if (w === widget) {
                return false
            }

            return this._rectsOverlap(left, top, width, height, w.getLeft(), w.getTop(), w.getWidth(), w.getHeight())

        }, this)
    }

    /**
     * Look for the best location to place a new widget of the given size.
     * @param {Number} width
     * @param {Number} height
     * @returns {{left: Number, top: Number}}
     */
    findWidgetPlace(width, height) {
        let layoutChanged = false

        /* Make sure the panel width is large enough and enlarge if necessary */
        if (this._width < width) {
            this._width = width
            layoutChanged = true
        }

        for (let y = 0; y < this._height; y++) {
            for (let x = 0; x < this._width; x++) {
                if (this.verifyWidgetLayout(x, y, width, height)) {
                    if (layoutChanged) {
                        this.updateUI()
                    }

                    return {left: x, top: y}
                }
            }
        }

        /* No place for the given widget on the current panel layout;
         * enlarge vertically and add to the bottom */
        let bottoms = ArrayUtils.sortKey(this.getWidgets().map(w => w.getTop() + w.getHeight()), e => e)

        let top = bottoms.length ? bottoms[bottoms.length - 1] : 0
        while (!this.verifyWidgetLayout(0, top, width, height)) {
            this._height++
            layoutChanged = true
        }

        if (layoutChanged) {
            this.updateUI()
        }

        return {left: 0, top: top}
    }

    _rectsOverlap(l1, t1, w1, h1, l2, t2, w2, h2) {
        return ((l1 >= l2 && l1 < l2 + w2) || (l2 >= l1 && l2 < l1 + w1)) &&
               ((t1 >= t2 && t1 < t2 + h2) || (t2 >= t1 && t2 < t1 + h1))
    }

    /**
     * @returns {Boolean}
     */
    isOptimizeSmallScreen() {
        return this._optimizeSmallScreen
    }

    /**
     * @param {Boolean} optimizeSmallScreen
     */
    setOptimizeSmallScreen(optimizeSmallScreen) {
        this._optimizeSmallScreen = optimizeSmallScreen
        this.updateUI()
    }

    onResize() {
        this.updateContainerLayout()
    }

    /**
     * Update panel container layout by recomputing cell width and assigning corresponding font size. Also refresh the
     * content of all contained widgets.
     */
    updateContainerLayout() {
        if (!this.isVisible()) {
            return
        }

        this._cellWidth = this._computeCellWidth()

        this.getBody().addClass('disable-transitions')

        this.getBody().css({
            'font-size': `${this._cellWidth}px`,
            'min-height': Math.ceil(this._cellWidth * this._height),
            'width': Math.ceil(this._cellWidth * this._width)
        })

        if (this._widgets) {
            this._widgets.forEach(function (w) {
                w.refreshContent()
            })
        }

        Theme.afterTransition(function () {
            this.removeClass('disable-transitions')
        }, this.getBody())
    }

    /**
     * Return the current cell width, in pixels.
     * @returns {Number}
     */
    getCellWidth() {
        if (this._cellWidth == null) {
            this._cellWidth = this._computeCellWidth()
        }

        return this._cellWidth
    }

    _computeCellWidth() {
        let pageContainerWidth = this.getPageHTML().parent().innerWidth()
        let panelWidthPercent = (!this._editEnabled || Window.isSmallScreen()) ? 100 : 75
        let width = pageContainerWidth * panelWidthPercent / 100

        /* Width is 0 before the panel is attached by using $body.width() when panel is not attached, we provide an
         * initial, valid em (font-size) for the panel, preventing unwanted transition effects from small sizes */
        width = width || Window.$body.width()

        /* When editing is enabled, extra 1.25rem margins are added we need to extract these from the useful width */
        if (this._editEnabled) {
            let margin = CSS.em2px(1.25) // TODO constant
            width -= 2 * margin
        }

        /* On large screens, account for a possible scroll bar, by subtracting another 1em */
        if (!Window.isSmallScreen()) {
            width -= CSS.em2px(1.25)
        }

        let cellWidth = width / this._width

        /* This rounding prevents (reduces) decentered rotation animations */
        cellWidth = Math.floor(cellWidth / 5) * 5

        return cellWidth
    }


    /* Widgets */

    /**
     * @returns {qtoggle.dashboard.widgets.Widget[]}
     */
    getWidgets() {
        if (this._widgets == null) {
            this.logger.debug('initializing widgets')

            this._initWidgets()
        }

        return this._widgets.slice()
    }

    _initWidgets() {
        if (!this._widgetsJSON) {
            this._widgetsJSON = [] /* A new panel */
        }

        this._widgets = this._widgetsFromJSON(this._widgetsJSON)

        this._widgets.forEach(function (w) {
            this.attachWidget(w)
        }, this)
    }

    /**
     * Look up a widget by id.
     * @param {String} id
     * @returns {?qtoggle.dashboard.widgets.Widget}
     */
    findWidget(id) {
        return this.getWidgets().find(function (w) {
            return w.getId() === id
        }) || null
    }

    /**
     * Attach widget content to panel container.
     * @param {qtoggle.dashboard.widgets.Widget} widget
     */
    attachWidget(widget) {
        let firstPlaceholderRow = this.getBody().children('div.panel-placeholder-row').first()
        if (firstPlaceholderRow.length) {
            /* In edit mode, has cell placeholders */
            firstPlaceholderRow.before(widget.getHTML())
        }
        else {
            this.getBody().append(widget.getHTML())
        }

        if (this._optionsForm) {
            this._optionsForm.updateSizeLimits()
        }
    }

    /**
     * Detach and remove widget from panel.
     * @param {qtoggle.dashboard.widgets.Widget} widget
     */
    removeWidget(widget) {
        let index = this.getWidgets().indexOf(widget)
        if (index >= 0) {
            this._widgets.splice(index, 1)
        }

        if (this._optionsForm) {
            this._optionsForm.updateSizeLimits()
        }

        widget.getHTML().remove()
    }

    /**
     * @param {typeof qtoggle.dashboard.widgets.Widget|String} type
     * @param {Object} [attributes] widget attributes
     * @returns {qtoggle.dashboard.widgets.Widget}
     */
    makeWidget(type, attributes = {}) {
        let Cls = type
        if (typeof type === 'string') {
            Cls = Widgets.find(type)
            if (!Cls) {
                this.logger.error(`cannot find widget type "${type}"`)
                return null
            }
        }

        let widget = new Cls()

        if (attributes.left == null || attributes.top == null) {
            let width = attributes.width || widget.getWidth()
            let height = attributes.height || widget.getHeight()
            let place = this.findWidgetPlace(width, height)
            ObjectUtils.assignDefault(attributes, place)
        }

        try {
            widget.fromJSON(attributes)
        }
        catch (e) {
            this.logger.errorStack('failed to restore widget (possibly corrupted section data)', e)
            return null
        }

        widget._panel = this
        if (widget.getId() === null) {
            /* Generate a unique id for this widget */
            widget.setId(this._makeWidgetId())
        }

        widget.updateLayout()
        widget.refreshContent()
        widget.updateState()

        return widget
    }

    /**
     * Duplicate a widget. Add, attach and select the new widget to the panel.
     * @param {qtoggle.dashboard.widgets.Widget} origWidget
     */
    duplicateWidget(origWidget) {
        let cls = origWidget.constructor
        this.logger.debug(`duplicating widget "${origWidget.getId()}" of type "${cls.category}/${cls.type}"`)

        let attributes = origWidget.toJSON()
        delete attributes.left
        delete attributes.top
        delete attributes.id

        let widget = this.makeWidget(cls, attributes)

        this._widgets.push(widget)
        this.attachWidget(widget)
        this.setSelectedWidget(widget)
        this.handleWidgetSelect(widget)

        if (Window.isSmallScreen()) {
            /* On small screens, handleWidgetSelect won't show the config, so we need to call it explicitly here */
            widget.showConfigForm()
        }

        /* Scroll to newly added widget */
        let pageHTML = this.getPageHTML()
        let cellWidth = this.getCellWidth()
        let scrollTop = cellWidth * (widget.getTop() - 0.5)
        pageHTML.scrollTop(scrollTop)

        Dashboard.savePanels()
    }

    /**
     * @returns {?qtoggle.dashboard.widgets.Widget}
     */
    getSelectedWidget() {
        return this.getWidgets().find(function (w) {
            return w.isSelected()
        }) || null
    }

    /**
     * @param {?qtoggle.dashboard.widgets.Widget} widget
     */
    setSelectedWidget(widget) {
        let widgets = this.getWidgets()
        widgets.forEach(function (w) {
            if (w !== widget && w.isSelected()) {
                w.setSelected(false)
            }
        })

        if (widget) {
            widget.setSelected(true)
        }
    }

    _widgetsFromJSON(json) {
        return json.map(function (j) {

            let attrs = ObjectUtils.copy(j, /* deep = */ true)
            let type = j.type
            delete attrs.type

            try {
                let w = this.makeWidget(type, attrs)
                if (w) {
                    return w
                }
                else {
                    this.logger.error(`failed to restore widget of class ${type} (possibly corrupted section data)`)
                    return null
                }
            }
            catch (e) {
                this.logger.errorStack(`failed to restore widget of class ${type} (possibly corrupted section data)`, e)
                return null
            }

        }, this).filter(w => w != null)
    }

    _makeWidgetId() {
        function generate() {
            let toHash = String(new Date().getTime() + Math.random() * 1000)
            return new Crypto.SHA256(toHash).toString().substring(0, 8)
        }

        let id = generate()

        /* Assure uniqueness */
        let allPanels = Dashboard.getAllPanels()
        while (true) {
            let exists = allPanels.find(function (panel) {
                if (!panel._widgetsJSON) {
                    return false /* New panel */
                }

                return Boolean(panel._widgetsJSON.find(function (j) {
                    return j.id === id
                }))
            })

            if (!exists) {
                break
            }

            id = generate()
        }

        return id
    }

    /**
     * @param {qtoggle.dashboard.widgets.Widget} widget
     */
    handleWidgetMove(widget) {
        Dashboard.savePanels()

        if (this._optionsForm) {
            this._optionsForm.updateSizeLimits()
        }
    }

    /**
     * @param {qtoggle.dashboard.widgets.Widget} widget
     */
    handleWidgetResize(widget) {
        Dashboard.savePanels()

        if (this._optionsForm) {
            this._optionsForm.updateSizeLimits()
        }
    }

    /**
     * @param {qtoggle.dashboard.widgets.Widget} widget
     */
    handleWidgetSelect(widget) {
        if (!widget) {
            return
        }

        if (!Window.isSmallScreen()) {
            widget.showConfigForm()
        }
    }


    /* Serialization */

    toJSON() {
        let json = super.toJSON()

        json.type = 'panel'

        /* Serialize initialized widgets */
        if (this._widgets == null) { /* Widgets not yet deserialized, use serialized value */
            json.widgets = this._widgetsJSON
        }
        else {
            json.widgets = this.getWidgets().map(function (w) {
                let j = w.toJSON()
                j.type = w.constructor.typeName

                return j
            })

            /* Also update internal serialized widgets */
            this._widgetsJSON = json.widgets.slice()
        }

        json.width = this._width
        json.height = this._height
        json.optimizeSmallScreen = this._optimizeSmallScreen

        return json
    }

    fromJSON(json) {
        super.fromJSON(json)

        if (json.width != null) {
            this._width = json.width
        }
        if (json.height != null) {
            this._height = json.height
        }
        if (json.optimizeSmallScreen != null) {
            this._optimizeSmallScreen = json.optimizeSmallScreen
        }

        if (json.widgets != null) {
            /* Widgets will be initialized later, when panel is shown */
            this._widgetsJSON = json.widgets.slice()
        }

        this.updateUI()

        this.logger = Logger.get(this.makeLogName())
    }


    /* History */

    getHistoryState() {
        let selectedWidget = this.getSelectedWidget()
        let selectedWidgetId = selectedWidget ? selectedWidget.getId() : null

        return {
            editEnabled: this._editEnabled,
            selectedWidgetId: selectedWidgetId
        }
    }

    restoreHistoryState(state) {
        if (!state) {
            return
        }

        if (state.editEnabled !== this.isEditEnabled()) {
            if (state.editEnabled) {
                this.enableEditing()
            }
            else {
                this.disableEditing()
            }
        }

        if (state.selectedWidgetId) {
            let widget = this.findWidget(state.selectedWidgetId)
            if (widget) {
                this.setSelectedWidget(widget)
            }
        }
    }


    /* Edit mode */

    /**
     * @returns {Boolean}
     */
    isEditEnabled() {
        return this._editEnabled
    }

    /**
     * Enable panel editing mode.
     */
    enableEditing() {
        if (this._editEnabled) {
            return
        }

        this._editEnabled = true
        this._enableEditing()
    }

    _enableEditing() {
        this.getHTML().addClass('edit')
        this._updatePlaceholderCells(this._width, this._height)
        this.updateContainerLayout()
        asap(function () {
            this.getHTML().addClass('placeholders-visible')
        }.bind(this))

        /* On a brand-new panel we prefer having the options bar displayed automatically, since the most likely action
         * is to add a new widget */
        if (!this._widgets) {
            this.openOptionsBar()
        }
    }

    /**
     * Disable panel editing mode.
     */
    disableEditing() {
        if (!this._editEnabled) {
            return
        }

        this._editEnabled = false
        this._disableEditing()
    }

    _disableEditing() {
        this.getHTML().removeClass('placeholders-visible')

        Theme.afterTransition(function () {
            this.getHTML().removeClass('edit')
            this.getBody().children('div.panel-placeholder-row').remove()
            this.updateContainerLayout()
        }.bind(this), this.getHTML())
    }


    /* Widget picker */

    /**
     * @returns {qtoggle.dashboard.widgets.WidgetPicker}
     */
    makeWidgetPicker() {
        let that = this
        let widgetPicker = new WidgetPicker(function (cls) {
            that._onWidgetPicked(cls)
        })

        if (!this.isEditEnabled()) {
            this.enableEditing()
        }

        return widgetPicker
    }

    _onWidgetPicked(cls) {
        this.logger.debug(`adding widget of type "${cls.category}/${cls.type}"`)

        let widget = this.makeWidget(cls)

        this._widgets.push(widget)
        this.attachWidget(widget)
        this.setSelectedWidget(widget)
        this.handleWidgetSelect(widget)

        if (Window.isSmallScreen()) {
            /* On small screens, handleWidgetSelect won't show the config, so we need to call it explicitly here */
            widget.showConfigForm()
        }

        /* Scroll to newly added widget */
        let pageHTML = this.getPageHTML()
        let cellWidth = this.getCellWidth()
        let scrollTop = cellWidth * (widget.getTop() - 0.5)
        pageHTML.scrollTop(scrollTop)

        Dashboard.savePanels()
    }


    /* Update */

    updateUI() {
        /* Sync path id with panel id */
        this.setPathId(this.getId())

        /* Update title from panel name */
        this.setTitle(this.getName())

        if (this._editEnabled) {
            this._updatePlaceholderCells(this.getWidth(), this.getHeight())
        }

        this.updateContainerLayout()
    }


    /* Options bar */

    /**
     * @returns {qui.forms.commonforms.OptionsForm}
     */
    getOptionsForm() {
        if (API.getCurrentAccessLevel() < API.ACCESS_LEVEL_ADMIN) {
            return null
        }

        if (!this._optionsForm) {
            this._optionsForm = new PanelOptionsForm(this)
        }

        return this._optionsForm
    }

    onOptionsChange(options) {
        this.setName(options.name)
        this.setWidth(options.width)
        this.setHeight(options.height)
        this.setOptimizeSmallScreen(options.optimizeSmallScreen)
        this.updateUI()

        Dashboard.savePanels()
    }

    makeOptionsBarContent() {
        return this.getOptionsForm()
    }


    /* Placeholder cells */

    _updatePlaceholderCells(width, height) {
        let element = this.getBody()

        /* Add new rows */
        while (element.children('div.panel-placeholder-row').length < height) {
            element.append(this._makePlaceholderCellRow())
        }

        /* Add new columns */
        let that = this
        element.children('div.panel-placeholder-row').each(function (y) {
            let row = $(this)
            while (row.children().length < width) {
                row.append(that._makePlaceholderCell(row.children().length, y))
            }
        })

        /* Remove old columns */
        element.children('div.panel-placeholder-row').each(function () {
            let row = $(this)
            while (row.children().length > width) {
                row.children(':last-child').remove()
            }
        })

        /* Remove old rows */
        while (element.children('div.panel-placeholder-row').length > height) {
            element.children('div.panel-placeholder-row:last').remove()
        }
    }

    _makePlaceholderCellRow() {
        return $('<div class="panel-placeholder-row"></div>')
    }

    _makePlaceholderCell(x, y) {
        return $('<div class="panel-placeholder-cell"></div>')
    }


    /* Various */

    onBecomeCurrent() {
        this.updateContainerLayout()

        if (this.getWidgets().length === 0) {
            this.enableEditing()
        }

        Dashboard.setCurrentPanel(this)
    }

    onClose() {
        if (this._editEnabled) {
            this.disableEditing()
        }

        if (this._widgets) {
            this.logger.debug('cleaning up widgets')

            this._widgets.forEach(function (widget) {
                widget.clearContent()
                widget.getHTML().remove()
            })

            /* Ensures that widgets will be recreated from scratch next time panel is shown */
            this._widgets = null
        }

        if (Dashboard.getCurrentPanel() === this) {
            Dashboard.setCurrentPanel(null)
        }
    }

    navigate(pathId) {
        switch (pathId) {
            case 'remove':
                return this.makeRemoveForm()

            case 'add':
                return this.makeWidgetPicker()

        }

        if (pathId.match(new RegExp('[a-f0-9]{8}'))) { /* Widget id */
            let widget = this.findWidget(pathId)
            if (!widget) {
                return
            }

            if (!this.isEditEnabled()) {
                this.enableEditing()
            }

            this.setSelectedWidget(widget)

            return widget.getConfigForm()
        }
    }

}


export default Panel
