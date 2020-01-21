
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
 * @class QToggle.DashboardSection.WidgetCategoryList
 * @extends qui.lists.List
 * @param {QToggle.DashboardSection.Widgets.WidgetPicker} widgetPicker
 * @param {Object[]} category
 * @param {QToggle.DashboardSection.Widgets.WidgetPicker.Callback} callback
 * @param {Object} [params]
 */
class WidgetCategoryList extends List {

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

    widgetClassToItem(widgetClass) {
        return new IconLabelListItem({
            label: widgetClass.displayName,
            icon: widgetClass.icon,
            data: {
                cls: widgetClass
            }
        })
    }

    onSelectionChange(item) {
        if (!item) {
            return
        }

        this._callback(item.getData().cls)
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
 * @callback QToggle.DashboardSection.Widgets.WidgetPicker.Callback
 * @param {Function} cls
 */

// TODO generalize this view into a category view or something

/**
 * @class QToggle.DashboardSection.Widgets.WidgetPicker
 * @mixes qui.pages.StructuredPageMixin
 * @param {QToggle.DashboardSection.Widgets.WidgetPicker.Callback} callback
 */
class WidgetPicker extends mix().with(StructuredPageMixin) {

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
        return $('<div class="dashboard-widget-picker"></div>')
    }

    makeBody() {
        let div = $('<div class="dashboard-widget-picker-body"></div>')

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
