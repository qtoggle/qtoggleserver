
import $ from '$qui/lib/jquery.module.js'

import {gettext}             from '$qui/base/i18n.js'
import {mix}                 from '$qui/base/mixwith.js'
import StockIcon             from '$qui/icons/stock-icon.js'
import {IconLabelListItem}   from '$qui/lists/common-items.js'
import List                  from '$qui/lists/list.js'
import {StructuredPageMixin} from '$qui/pages/common-pages.js'

import * as Widgets from './widgets.js'


const WIDGET_ICON = new StockIcon({name: 'widget', stockName: 'qtoggle'})


/**
 * @alias qtoggle.dashboard.widgets.WidgetCategoryList
 * @extends qui.lists.List
 */
class WidgetCategoryList extends List {

    /**
     * @constructs
     * @param {qtoggle.dashboard.widgets.WidgetPicker} widgetPicker
     * @param {Object} categoryInfo
     * @param {qtoggle.dashboard.widgets.WidgetPicker.Callback} callback
     */
    constructor(widgetPicker, categoryInfo, callback) {
        super({
            title: '',
            minimizable: true,
            minimized: true
        })

        this.setTitle(categoryInfo.name)
        if (categoryInfo.icon) {
            this.setIcon(categoryInfo.icon)
        }

        this._widgetPicker = widgetPicker
        this._callback = callback

        this.setItems(categoryInfo.widgetClasses.map(this.widgetClassToItem))
    }

    /**
     * @param {typeof qtoggle.dashboard.widgets.Widget} widgetClass
     * @returns {qui.lists.ListItem}
     */
    widgetClassToItem(widgetClass) {
        return new IconLabelListItem({
            label: widgetClass.displayName,
            icon: widgetClass.icon,
            data: {
                cls: widgetClass
            }
        })
    }

    onSelectionChange(newItem, newIndex, oldItem, oldIndex) {
        if (!newItem) {
            return
        }

        this._callback(newItem.getData().cls)
    }

    onUnminimize() {
        /* Minimize all other lists when this is unminimized */
        this._widgetPicker._categoryLists.forEach(function (list) {
            if (list === this) {
                return
            }

            list.minimize()
        }, this)
    }

}

/**
 * @callback qtoggle.dashboard.widgets.WidgetPicker.Callback
 * @param {typeof qtoggle.dashboard.widgets.Widget} cls
 */

// TODO generalize this view into a category view or something

/**
 * @alias qtoggle.dashboard.widgets.WidgetPicker
 * @mixes qui.pages.StructuredPageMixin
 */
class WidgetPicker extends mix().with(StructuredPageMixin) {

    /**
     * @constructs
     * @param {qtoggle.dashboard.widgets.WidgetPicker.Callback} callback
     */
    constructor(callback) {
        super({
            title: gettext('Pick A Widget'),
            icon: WIDGET_ICON,
            closable: true,
            column: true,
            pathId: 'add',
            keepPrevVisible: true,
            transparent: false
        })

        this._categoryLists = []
        this._callback = callback
    }

    makeHTML() {
        return $('<div></div>', {class: 'dashboard-widget-picker'})
    }

    makeBody() {
        let div = $('<div></div>', {class: 'dashboard-widget-picker-body'})

        let categories = Widgets.getRegistry()
        categories.forEach(function (categoryInfo) {
            let that = this
            let list = new WidgetCategoryList(this, categoryInfo, function (cls) {
                that._onWidgetPicked(cls)
            })
            this._categoryLists.push(list)
            div.append(list.getHTML())
        }, this)

        return div
    }

    _onWidgetPicked(cls) {
        this.close().then(() => this._callback(cls))
    }

}


export default WidgetPicker
