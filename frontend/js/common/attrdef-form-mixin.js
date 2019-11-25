import {gettext}                  from '$qui/base/i18n.js'
import {Mixin}                    from '$qui/base/mixwith.js'
import {
    CheckField, ComboField, LabelsField, NumericField, PasswordField, SliderField, TextField, UpDownField
}                                 from '$qui/forms/common-fields.js'
import {ValidationError}          from '$qui/forms/forms.js'
import * as ArrayUtils            from '$qui/utils/array.js'
import * as HTML                  from '$qui/utils/html.js'
import * as ObjectUtils           from '$qui/utils/object.js'
import * as StringUtils           from '$qui/utils/string.js'


export default Mixin((superclass = Object) => {

    class AttrdefFormMixin extends superclass /** @lends AttrdefFormMixin */ {

        fieldAttrsFromAttrdef(name, def) {
            let field = {
                name: `attr_${name}`,
                description: HTML.escape(def.description || ''),
                required: def.required,
                readonly: !def.modifiable,
                unit: def.unit,
                separator: def.separator,
                label: def.display_name || StringUtils.title(name.replace(new RegExp('[^a-z0-9]', 'ig'), ' '))
            }

            if (def.choices && def.modifiable) {
                field.class = ComboField
                field.choices = def.choices.map(function (c) {
                    if (ObjectUtils.isObject(c)) {
                        return {value: c.value, label: c.display_name || StringUtils.title(c.value.toString())}
                    }
                    else { /* older choices format compatibility shim */
                        return {value: c, label: c}
                    }
                })
            }
            else {
                switch (def.type) {
                    case 'boolean': {
                        field.class = CheckField
                        break
                    }

                    case 'number': {
                        let count = 1e6 /* Some large number */
                        let decimals = 0
                        let step = def.step

                        if (def.integer) {
                            if (step == null) {
                                step = 1
                            }
                        }
                        else { /* Generic float value */
                            if (step == null) {
                                step = 0.01
                            }
                            let stepStr = String(step)
                            if (stepStr.indexOf('.') >= 0) {
                                decimals = stepStr.length - stepStr.indexOf('.') - 1
                            }
                        }

                        if (def.min != null && def.max != null) {
                            count = (def.max - def.min) / step + 1
                        }

                        if (count <= 101) {
                            field.class = SliderField
                            let ticks = []
                            for (let v = def.min; v <= def.max; v += step) {
                                ticks.push({value: v, label: v})
                            }
                            field.ticks = ticks
                            field.ticksStep = Math.round((count - 1) / 5)
                            field.snapMode = 1
                        }
                        else { /* Many choices */
                            field.class = NumericField
                            field.continuousChange = true

                            field.validate = function (value) {
                                if (!value && !def.required) {
                                    return
                                }

                                let numValue
                                if (def.integer) {
                                    if (!new RegExp('^-?\\d+$').test(value)) {
                                        throw new ValidationError(gettext('Value must be a valid integer number.'))
                                    }

                                    numValue = parseInt(value)
                                }
                                else { /* Assuming float value */
                                    if (!new RegExp('^-?\\d+.?\\d*$').test(value)) {
                                        throw new ValidationError(gettext('Value must be a valid real number.'))
                                    }

                                    numValue = parseFloat(value)
                                }

                                if (def.min != null && def.step) {
                                    if ((numValue - def.min) % step) {
                                        let msg = StringUtils.formatPercent(
                                            gettext('Value must be %(min)s + a multiple of %(step)s.'),
                                            {min: def.min, step: def.step}
                                        )
                                        throw new ValidationError(msg)
                                    }
                                }
                            }
                        }

                        break
                    }

                    case 'string': {
                        if (name.indexOf('password') >= 0) {
                            field.class = PasswordField
                            field.autocomplete = false
                            field.clearEnabled = true
                            field.clearPlaceholder = true
                            field.placeholder = `(${gettext('hidden')})`
                        }
                        else {
                            field.class = TextField
                        }

                        field.continuousChange = true

                        field.validate = function (value) {
                            if (def.min != null && value.length < def.min) {
                                let msg = StringUtils.formatPercent(
                                    gettext('Enter a text of at least %(count)s characters.'),
                                    {count: def.min}
                                )
                                throw new ValidationError(msg)
                            }
                            if (def.max != null && value.length > def.max) {
                                let msg = StringUtils.formatPercent(
                                    gettext('Enter a text of at most %(count)s characters.'),
                                    {count: def.max}
                                )
                                throw new ValidationError(msg)
                            }
                            if (def.regex && value && !value.match(new RegExp(def.regex))) {
                                throw new ValidationError(gettext('The entered text is invalid.'))
                            }
                        }

                        break
                    }

                    case 'flags': { // TODO replace with list of strings
                        field.class = LabelsField

                        break
                    }
                }
            }

            /* Add custom validator */
            if (def.validate) {
                let oldValidate = field.validate
                field.validate = function (value, data) {
                    /* Remove the leading "_attr" */
                    data = ObjectUtils.mapKey(data, function (key) {
                        if (key.startsWith('attr_')) {
                            return key.substring(5)
                        }
                        else {
                            return key
                        }
                    })
                    if (oldValidate) {
                        let result = oldValidate(value, data)
                        if (result) {
                            return result
                        }
                    }

                    return def.validate(value, data)
                }
            }

            return field
        }

        fieldsFromAttrdefs({
            attrdefs = {}, extraFieldOptions = {}, initialData = {}, provisioning = [], noUpdated = [], startIndex = 0,
            fieldChangeWarnings = true
        } = {}) {
            let defEntries = ArrayUtils.sortKey(Object.entries(attrdefs), e => e[0])
            ArrayUtils.stableSortKey(defEntries, e => e[1].order || 1000)

            let newValues = {}

            let notKnown = false
            defEntries.forEach(function (entry, index) {
                let name = entry[0]
                let def = ObjectUtils.copy(entry[1], /* deep = */ true)

                if (!notKnown && !def.known) {
                    def.separator = true
                }

                if (!def.known) {
                    notKnown = true
                }

                /* Old field state */
                let field = this.getField(`attr_${name}`)
                let fieldAttrs = this.fieldAttrsFromAttrdef(name, def)
                if (name in extraFieldOptions) {
                    Object.assign(fieldAttrs, extraFieldOptions[name])
                }

                let newValue = def.valueToUI(initialData[name])
                if (name in initialData) {
                    fieldAttrs.initialValue = newValue
                }

                if (field) {
                    let oldValue = field.getValue()
                    if (oldValue !== newValue) {
                        if (def.modifiable && noUpdated.indexOf(name) < 0 && fieldChangeWarnings) {
                            if (!field.hasError() && !field.hasWarning()) {
                                field.setWarning(gettext('Value has been updated in the meantime.'))
                            }
                        }
                        else {
                            newValues[field.getName()] = newValue
                        }
                    }

                    field.setLabel(fieldAttrs.label)
                    field.setDescription(fieldAttrs.description)
                    field.setUnit(fieldAttrs.unit)
                    field.setSeparator(!!fieldAttrs.separator)
                    field.setRequired(!!fieldAttrs.required)
                    field.setReadonly(!!fieldAttrs.readonly)
                }
                else {
                    let FieldClass = fieldAttrs.class
                    field = new FieldClass(fieldAttrs)
                    this.addField(startIndex + index, field)
                }

                if (provisioning.indexOf(name) >= 0) {
                    field.setWarning(gettext('Value will be provisioned when device gets back online.'))
                }

            }, this)

            /* Mark fields that are no longer defined as removed */
            this.getFields().forEach(function (field) {
                let name = field.getName()

                if (!name.startsWith('attr_')) {
                    return
                }
                if (name.substring(5) in attrdefs) {
                    return
                }

                this.removeField(name)
            }, this)

            /* Update with new values */
            if (Object.keys(newValues).length) {
                this.setData(newValues)
            }
        }

    }

    return AttrdefFormMixin

})
