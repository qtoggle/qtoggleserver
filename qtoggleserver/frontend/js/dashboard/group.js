
import {gettext}           from '$qui/base/i18n.js'
import {mix}               from '$qui/base/mixwith.js'
import {CompositeField}    from '$qui/forms/common-fields/common-fields.js'
import {PushButtonField}   from '$qui/forms/common-fields/common-fields.js'
import {TextField}         from '$qui/forms/common-fields/common-fields.js'
import {OptionsForm}       from '$qui/forms/common-forms/common-forms.js'
import {ValidationError}   from '$qui/forms/forms.js'
import {IconLabelListItem} from '$qui/lists/common-items/common-items.js'
import {PageList}          from '$qui/lists/common-lists/common-lists.js'
import * as ArrayUtils     from '$qui/utils/array.js'

import * as AuthAPI from '$app/api/auth.js'
import * as Utils   from '$app/utils.js'

import AddPanelGroupForm        from './add-panel-group-form.js'
import * as Dashboard           from './dashboard.js'
import Panel                    from './panel.js'
import PanelGroupCompositeMixin from './panel-group-composite.js'


class GroupOptionsForm extends OptionsForm {

    constructor(group) {
        super({
            page: group,
            fields: [
                new TextField({
                    name: 'name',
                    label: gettext('Name'),
                    required: true,
                    maxLength: 64
                }),
                new CompositeField({
                    name: 'actionButtons',
                    label: gettext('Actions'),
                    separator: true,
                    flow: 'vertical',
                    fields: [
                        new PushButtonField({
                            name: 'remove',
                            caption: gettext('Remove'),
                            style: 'danger',
                            onClick(form) {
                                let panel = form._group
                                panel.pushPage(panel.makeRemoveForm())
                            }
                        })
                    ]
                })
            ],
            initialData: {
                name: group.getName()
            }
        })

        this._group = group
    }

    validateField(name, value, data) {
        switch (name) {
            case 'name': {
                let child = this._group.getParent().findChildByName(value)
                if (child && child !== this._group) {
                    throw new ValidationError(gettext('This name already exists!'))
                }
            }
        }
    }

}

/**
 * @alias qtoggle.dashboard.Group
 * @extends qui.lists.commonlists.PageList
 * @mixes qtoggle.dashboard.PanelGroupCompositeMixin
 */
class Group extends mix(PageList).with(PanelGroupCompositeMixin) {

    /**
     * @constructs
     * @param {...args} [args]
     */
    constructor({...args} = {}) {
        Object.assign(args, {
            pathId: '',
            title: '',
            icon: Dashboard.GROUP_ICON,
            columnLayout: true,
            searchEnabled: true,
            addEnabled: AuthAPI.getCurrentAccessLevel() >= AuthAPI.ACCESS_LEVEL_ADMIN
        })

        super(args)

        this._children = []
    }

    init() {
        this.updateUI()
    }

    isPrevKeptVisible() {
        /* Keep at most 3 elements visible */
        return this.getContext().getSize() - this.getContextIndex() < 3
    }

    /**
     * @returns {qtoggle.dashboard.PanelGroupCompositeMixin[]}
     */
    getChildren() {
        return this._children.slice()
    }

    /**
     * @returns {qtoggle.dashboard.Panel[]}
     */
    getPanelsRec() {
        return this._children.reduce(function (l, c) {
            if (c instanceof Panel) {
                return l.concat([c])
            }
            else {
                return l.concat(c.getPanelsRec())
            }
        }, [])
    }

    /**
     * Look up child by id.
     * @param {String} id
     * @returns {?qtoggle.dashboard.PanelGroupCompositeMixin}
     */
    findChildById(id) {
        return this._children.find(function (child) {
            return child.getId() === id
        })
    }

    /**
     * Look up child by name.
     * @param {String} name
     * @returns {?qtoggle.dashboard.PanelGroupCompositeMixin}
     */
    findChildByName(name) {
        return this.findChildById(Utils.nameToId(name))
    }

    /**
     * Add a child to group.
     * @param {qtoggle.dashboard.PanelGroupCompositeMixin} child
     */
    addChild(child) {
        this._children.push(child)

        this.updateUI()
    }

    /**
     * Remove a child from group.
     * @param {qtoggle.dashboard.PanelGroupCompositeMixin} child
     */
    removeChild(child) {
        let index = this._children.indexOf(child)
        this._children.splice(index, 1)

        this.updateUI()
    }

    /**
     * Serialize group to a JSON object.
     * @returns {Object}
     */
    toJSON() {
        let json = super.toJSON()

        json.type = 'group'
        json.children = this._children.map(c => c.toJSON())

        return json
    }

    /**
     * Load group from a serialized JSON object.
     * @param {Object} json
     */
    fromJSON(json) {
        super.fromJSON(json)

        /* Sync path id with group id, but ignore root group */
        if (this._parent) {
            this.setPathId(this.getId())
        }

        /* Update title from panel name */
        this.setTitle(this.getName())

        if (json.children != null) {
            this._children = []
            json.children.forEach(function (j) {
                let c
                if (j.type === 'panel') {
                    c = new Panel({parent: this})
                }
                else {
                    c = new Group({parent: this})
                }

                c.fromJSON(j)

                this._children.push(c)
            }, this)
        }
    }

    updateUI(recursive = false) {
        this.setTitle(this.getName())

        /* Update path id from title, unless root group */
        if (this._parent) {
            this.setPathId(this.getId())
        }

        let children = this.getChildren()

        ArrayUtils.sortKey(children, c => Utils.alphaNumSortKey(c.getName()))

        let items = children.map(function (p) {
            if (p instanceof Group) {
                return this.groupToItem(p)
            }
            else { /* Assuming panel */
                return this.panelToItem(p)
            }
        }, this)

        let oldSelectedItems = this.getSelectedItems()
        let oldSelectedChild = oldSelectedItems.length ? oldSelectedItems[0].getData() : null

        this.setItems(items)

        if (oldSelectedChild) {
            let newSelectedItem = items.find(function (item) {
                return (item.getData().getId() === oldSelectedChild.getId())
            })

            if (newSelectedItem) {
                this.setSelectedItems([newSelectedItem])
            }
        }

        if (recursive) {
            children.forEach(c => c.updateUI(recursive))
        }
    }

    onAdd() {
        return this.pushPage(this.makeAddForm())
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeAddForm() {
        return new AddPanelGroupForm(this)
    }

    /**
     * Create list item from panel.
     * @param {qtoggle.dashboard.Panel} panel
     * @returns {qui.lists.ListItem}
     */
    panelToItem(panel) {
        return new IconLabelListItem({
            label: panel.getName(),
            icon: Dashboard.PANEL_ICON,
            data: panel
        })
    }

    /**
     * Create list item from group.
     * @param {qtoggle.dashboard.Group} group
     * @returns {qui.lists.ListItem}
     */
    groupToItem(group) {
        return new IconLabelListItem({
            label: group.getName(),
            icon: Dashboard.GROUP_ICON,
            data: group
        })
    }

    onSelectionChange(oldItems, newItems) {
        if (newItems.length) {
            return this.pushPage(newItems[0].getData())
        }
    }

    onCloseNext(next) {
        let selectedItems = this.getSelectedItems()
        if (selectedItems.length && selectedItems[0].getData() === next) {
            this.setSelectedItems([])
        }
    }

    onOptionsChange(options) {
        this.setName(options.name)
        this.updateUI()
        this.save()
    }

    makeOptionsBarContent() {
        if (this.getParent()) { /* Not root */
            return new GroupOptionsForm(this)
        }
    }

    navigate(pathId) {
        let admin = AuthAPI.getCurrentAccessLevel() >= AuthAPI.ACCESS_LEVEL_ADMIN

        if (pathId === 'add' && admin) {
            return this.makeAddForm()
        }
        else if (pathId === 'remove' && admin) {
            return this.makeRemoveForm()
        }
        else { /* A panel/group name */
            let child = this.findChildById(pathId)
            if (child) {
                this.setSelectedChild(child)
                return child
            }
        }
    }

    setSelectedChild(child) {
        let item = this.getItems().find(item => item.getData() === child)
        if (item) {
            this.setSelectedItems([item])
        }
        else {
            this.setSelectedItems([])
        }
    }

}


export default Group
