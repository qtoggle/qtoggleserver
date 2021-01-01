
import $ from '$qui/lib/jquery.module.js'

import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields/common-fields.js'
import {ColorComboField} from '$qui/forms/common-fields/common-fields.js'
import {TextField}       from '$qui/forms/common-fields/common-fields.js'
import StockIcon         from '$qui/icons/stock-icon.js'
import * as Theme        from '$qui/theme.js'

import * as Widgets     from '$app/dashboard/widgets/widgets.js'
import Widget           from '$app/dashboard/widgets/widget.js'
import WidgetConfigForm from '$app/dashboard/widgets/widget-config-form.js'


class ConfigForm extends WidgetConfigForm {

    constructor({...args}) {
        super({
            fields: [
                new TextField({
                    name: 'url',
                    label: gettext('URL'),
                    required: true
                }),
                new ColorComboField({
                    name: 'backgroundColor',
                    label: gettext('Background Color'),
                    filterEnabled: true,
                    required: true
                }),
                new CheckField({
                    name: 'preserveAspectRatio',
                    label: gettext('Preserve Aspect Ratio')
                })
            ],
            ...args
        })
    }

}


/**
 * @alias qtoggle.dashboard.widgets.media.MJPEGVideo
 * @extends qtoggle.dashboard.widgets.Widget
 */
class MJPEGVideo extends Widget {

    static category = gettext('Media')
    static displayName = gettext('MJPEG Video')
    static typeName = 'MJPEGVideo'
    static icon = new StockIcon({name: 'widget-video', stockName: 'qtoggle'})
    static ConfigForm = ConfigForm
    static vResizable = true
    static hResizable = true
    static hasFrame = true


    /**
     * @constructs
     */
    constructor() {
        super()

        this._url = null
        this._backgroundColor = '@background-color'
        this._preserveAspectRatio = true

        this._videoElement = null
    }

    isValid() {
        return Boolean(this._url)
    }

    makeContent(width, height) {
        let spacer = $('<div></div>', {class: 'dashboard-mjpeg-video-spacer'})
        spacer.css('background', Theme.getColor(this._backgroundColor))

        let container = $('<div></div>', {class: 'dashboard-mjpeg-video-container'})
        spacer.append(container)

        this._clearVideoElement()
        this._videoElement = this._makeVideoElement(width, height)
        container.append(this._videoElement)

        return spacer
    }

    clearContent() {
        this._clearVideoElement()
        super.clearContent()
    }

    _makeVideoElement(width, height) {
        let videoElement = $('<img>', {class: 'dashboard-mjpeg-video-element', src: this._url})

        if (!this._preserveAspectRatio) {
            videoElement.css('height', '100%')
        }

        return videoElement
    }

    _clearVideoElement() {
        if (this._videoElement) {
            this._videoElement.attr('src', '#')
            this._videoElement = null
        }
    }

    configToJSON() {
        return {
            url: this._url,
            backgroundColor: this._backgroundColor,
            preserveAspectRatio: this._preserveAspectRatio
        }
    }

    configFromJSON(json) {
        if (json.url != null) {
            this._url = json.url
        }
        if (json.backgroundColor) {
            this._backgroundColor = json.backgroundColor
        }
        if (json.preserveAspectRatio != null) {
            this._preserveAspectRatio = json.preserveAspectRatio
        }
    }

}

Widgets.register(MJPEGVideo)


export default MJPEGVideo
