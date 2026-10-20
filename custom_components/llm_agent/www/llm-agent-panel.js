//#region node_modules/@lit/reactive-element/css-tag.js
var e = globalThis, t = e.ShadowRoot && (e.ShadyCSS === void 0 || e.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, n = Symbol(), r = /* @__PURE__ */ new WeakMap(), i = class {
	constructor(e, t, r) {
		if (this._$cssResult$ = !0, r !== n) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
		this.cssText = e, this.t = t;
	}
	get styleSheet() {
		let e = this.o, n = this.t;
		if (t && e === void 0) {
			let t = n !== void 0 && n.length === 1;
			t && (e = r.get(n)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), t && r.set(n, e));
		}
		return e;
	}
	toString() {
		return this.cssText;
	}
}, a = (e) => new i(typeof e == "string" ? e : e + "", void 0, n), o = (e, ...t) => new i(e.length === 1 ? e[0] : t.reduce((t, n, r) => t + ((e) => {
	if (!0 === e._$cssResult$) return e.cssText;
	if (typeof e == "number") return e;
	throw Error("Value passed to 'css' function must be a 'css' function result: " + e + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
})(n) + e[r + 1], e[0]), e, n), s = (n, r) => {
	if (t) n.adoptedStyleSheets = r.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
	else for (let t of r) {
		let r = document.createElement("style"), i = e.litNonce;
		i !== void 0 && r.setAttribute("nonce", i), r.textContent = t.cssText, n.appendChild(r);
	}
}, c = t ? (e) => e : (e) => e instanceof CSSStyleSheet ? ((e) => {
	let t = "";
	for (let n of e.cssRules) t += n.cssText;
	return a(t);
})(e) : e, { is: l, defineProperty: u, getOwnPropertyDescriptor: d, getOwnPropertyNames: f, getOwnPropertySymbols: p, getPrototypeOf: m } = Object, h = globalThis, ee = h.trustedTypes, te = ee ? ee.emptyScript : "", ne = h.reactiveElementPolyfillSupport, re = (e, t) => e, g = {
	toAttribute(e, t) {
		switch (t) {
			case Boolean:
				e = e ? te : null;
				break;
			case Object:
			case Array: e = e == null ? e : JSON.stringify(e);
		}
		return e;
	},
	fromAttribute(e, t) {
		let n = e;
		switch (t) {
			case Boolean:
				n = e !== null;
				break;
			case Number:
				n = e === null ? null : Number(e);
				break;
			case Object:
			case Array: try {
				n = JSON.parse(e);
			} catch {
				n = null;
			}
		}
		return n;
	}
}, ie = (e, t) => !l(e, t), ae = {
	attribute: !0,
	type: String,
	converter: g,
	reflect: !1,
	useDefault: !1,
	hasChanged: ie
};
Symbol.metadata ??= Symbol("metadata"), h.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
var _ = class extends HTMLElement {
	static addInitializer(e) {
		this._$Ei(), (this.l ??= []).push(e);
	}
	static get observedAttributes() {
		return this.finalize(), this._$Eh && [...this._$Eh.keys()];
	}
	static createProperty(e, t = ae) {
		if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
			let n = Symbol(), r = this.getPropertyDescriptor(e, n, t);
			r !== void 0 && u(this.prototype, e, r);
		}
	}
	static getPropertyDescriptor(e, t, n) {
		let { get: r, set: i } = d(this.prototype, e) ?? {
			get() {
				return this[t];
			},
			set(e) {
				this[t] = e;
			}
		};
		return {
			get: r,
			set(t) {
				let a = r?.call(this);
				i?.call(this, t), this.requestUpdate(e, a, n);
			},
			configurable: !0,
			enumerable: !0
		};
	}
	static getPropertyOptions(e) {
		return this.elementProperties.get(e) ?? ae;
	}
	static _$Ei() {
		if (this.hasOwnProperty(re("elementProperties"))) return;
		let e = m(this);
		e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
	}
	static finalize() {
		if (this.hasOwnProperty(re("finalized"))) return;
		if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(re("properties"))) {
			let e = this.properties, t = [...f(e), ...p(e)];
			for (let n of t) this.createProperty(n, e[n]);
		}
		let e = this[Symbol.metadata];
		if (e !== null) {
			let t = litPropertyMetadata.get(e);
			if (t !== void 0) for (let [e, n] of t) this.elementProperties.set(e, n);
		}
		this._$Eh = /* @__PURE__ */ new Map();
		for (let [e, t] of this.elementProperties) {
			let n = this._$Eu(e, t);
			n !== void 0 && this._$Eh.set(n, e);
		}
		this.elementStyles = this.finalizeStyles(this.styles);
	}
	static finalizeStyles(e) {
		let t = [];
		if (Array.isArray(e)) {
			let n = new Set(e.flat(1 / 0).reverse());
			for (let e of n) t.unshift(c(e));
		} else e !== void 0 && t.push(c(e));
		return t;
	}
	static _$Eu(e, t) {
		let n = t.attribute;
		return !1 === n ? void 0 : typeof n == "string" ? n : typeof e == "string" ? e.toLowerCase() : void 0;
	}
	constructor() {
		super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
	}
	_$Ev() {
		this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((e) => e(this));
	}
	addController(e) {
		(this._$EO ??= /* @__PURE__ */ new Set()).add(e), this.renderRoot !== void 0 && this.isConnected && e.hostConnected?.();
	}
	removeController(e) {
		this._$EO?.delete(e);
	}
	_$E_() {
		let e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
		for (let n of t.keys()) this.hasOwnProperty(n) && (e.set(n, this[n]), delete this[n]);
		e.size > 0 && (this._$Ep = e);
	}
	createRenderRoot() {
		let e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
		return s(e, this.constructor.elementStyles), e;
	}
	connectedCallback() {
		this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((e) => e.hostConnected?.());
	}
	enableUpdating(e) {}
	disconnectedCallback() {
		this._$EO?.forEach((e) => e.hostDisconnected?.());
	}
	attributeChangedCallback(e, t, n) {
		this._$AK(e, n);
	}
	_$ET(e, t) {
		let n = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, n);
		if (r !== void 0 && !0 === n.reflect) {
			let i = (n.converter?.toAttribute === void 0 ? g : n.converter).toAttribute(t, n.type);
			this._$Em = e, i == null ? this.removeAttribute(r) : this.setAttribute(r, i), this._$Em = null;
		}
	}
	_$AK(e, t) {
		let n = this.constructor, r = n._$Eh.get(e);
		if (r !== void 0 && this._$Em !== r) {
			let e = n.getPropertyOptions(r), i = typeof e.converter == "function" ? { fromAttribute: e.converter } : e.converter?.fromAttribute === void 0 ? g : e.converter;
			this._$Em = r;
			let a = i.fromAttribute(t, e.type);
			this[r] = a ?? this._$Ej?.get(r) ?? a, this._$Em = null;
		}
	}
	requestUpdate(e, t, n, r = !1, i) {
		if (e !== void 0) {
			let a = this.constructor;
			if (!1 === r && (i = this[e]), n ??= a.getPropertyOptions(e), !((n.hasChanged ?? ie)(i, t) || n.useDefault && n.reflect && i === this._$Ej?.get(e) && !this.hasAttribute(a._$Eu(e, n)))) return;
			this.C(e, t, n);
		}
		!1 === this.isUpdatePending && (this._$ES = this._$EP());
	}
	C(e, t, { useDefault: n, reflect: r, wrapped: i }, a) {
		n && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(e) && (this._$Ej.set(e, a ?? t ?? this[e]), !0 !== i || a !== void 0) || (this._$AL.has(e) || (this.hasUpdated || n || (t = void 0), this._$AL.set(e, t)), !0 === r && this._$Em !== e && (this._$Eq ??= /* @__PURE__ */ new Set()).add(e));
	}
	async _$EP() {
		this.isUpdatePending = !0;
		try {
			await this._$ES;
		} catch (e) {
			Promise.reject(e);
		}
		let e = this.scheduleUpdate();
		return e != null && await e, !this.isUpdatePending;
	}
	scheduleUpdate() {
		return this.performUpdate();
	}
	performUpdate() {
		if (!this.isUpdatePending) return;
		if (!this.hasUpdated) {
			if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
				for (let [e, t] of this._$Ep) this[e] = t;
				this._$Ep = void 0;
			}
			let e = this.constructor.elementProperties;
			if (e.size > 0) for (let [t, n] of e) {
				let { wrapped: e } = n, r = this[t];
				!0 !== e || this._$AL.has(t) || r === void 0 || this.C(t, void 0, n, r);
			}
		}
		let e = !1, t = this._$AL;
		try {
			e = this.shouldUpdate(t), e ? (this.willUpdate(t), this._$EO?.forEach((e) => e.hostUpdate?.()), this.update(t)) : this._$EM();
		} catch (t) {
			throw e = !1, this._$EM(), t;
		}
		e && this._$AE(t);
	}
	willUpdate(e) {}
	_$AE(e) {
		this._$EO?.forEach((e) => e.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
	}
	_$EM() {
		this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
	}
	get updateComplete() {
		return this.getUpdateComplete();
	}
	getUpdateComplete() {
		return this._$ES;
	}
	shouldUpdate(e) {
		return !0;
	}
	update(e) {
		this._$Eq &&= this._$Eq.forEach((e) => this._$ET(e, this[e])), this._$EM();
	}
	updated(e) {}
	firstUpdated(e) {}
};
_.elementStyles = [], _.shadowRootOptions = { mode: "open" }, _[re("elementProperties")] = /* @__PURE__ */ new Map(), _[re("finalized")] = /* @__PURE__ */ new Map(), ne?.({ ReactiveElement: _ }), (h.reactiveElementVersions ??= []).push("2.1.2");
//#endregion
//#region node_modules/lit-html/lit-html.js
var oe = globalThis, se = (e) => e, ce = oe.trustedTypes, v = ce ? ce.createPolicy("lit-html", { createHTML: (e) => e }) : void 0, le = "$lit$", y = `lit$${Math.random().toFixed(9).slice(2)}$`, ue = "?" + y, de = `<${ue}>`, fe = document, b = () => fe.createComment(""), pe = (e) => e === null || typeof e != "object" && typeof e != "function", me = Array.isArray, he = (e) => me(e) || typeof e?.[Symbol.iterator] == "function", ge = "[ 	\n\f\r]", _e = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, ve = /-->/g, ye = />/g, be = RegExp(`>|${ge}(?:([^\\s"'>=/]+)(${ge}*=${ge}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`, "g"), x = /'/g, xe = /"/g, Se = /^(?:script|style|textarea|title)$/i, S = ((e) => (t, ...n) => ({
	_$litType$: e,
	strings: t,
	values: n
}))(1), Ce = Symbol.for("lit-noChange"), C = Symbol.for("lit-nothing"), we = /* @__PURE__ */ new WeakMap(), Te = fe.createTreeWalker(fe, 129);
function Ee(e, t) {
	if (!me(e) || !e.hasOwnProperty("raw")) throw Error("invalid template strings array");
	return v === void 0 ? t : v.createHTML(t);
}
var De = (e, t) => {
	let n = e.length - 1, r = [], i, a = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", o = _e;
	for (let t = 0; t < n; t++) {
		let n = e[t], s, c, l = -1, u = 0;
		for (; u < n.length && (o.lastIndex = u, c = o.exec(n), c !== null);) u = o.lastIndex, o === _e ? c[1] === "!--" ? o = ve : c[1] === void 0 ? c[2] === void 0 ? c[3] !== void 0 && (o = be) : (Se.test(c[2]) && (i = RegExp("</" + c[2], "g")), o = be) : o = ye : o === be ? c[0] === ">" ? (o = i ?? _e, l = -1) : c[1] === void 0 ? l = -2 : (l = o.lastIndex - c[2].length, s = c[1], o = c[3] === void 0 ? be : c[3] === "\"" ? xe : x) : o === xe || o === x ? o = be : o === ve || o === ye ? o = _e : (o = be, i = void 0);
		let d = o === be && e[t + 1].startsWith("/>") ? " " : "";
		a += o === _e ? n + de : l >= 0 ? (r.push(s), n.slice(0, l) + le + n.slice(l) + y + d) : n + y + (l === -2 ? t : d);
	}
	return [Ee(e, a + (e[n] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), r];
}, w = class e {
	constructor({ strings: t, _$litType$: n }, r) {
		let i;
		this.parts = [];
		let a = 0, o = 0, s = t.length - 1, c = this.parts, [l, u] = De(t, n);
		if (this.el = e.createElement(l, r), Te.currentNode = this.el.content, n === 2 || n === 3) {
			let e = this.el.content.firstChild;
			e.replaceWith(...e.childNodes);
		}
		for (; (i = Te.nextNode()) !== null && c.length < s;) {
			if (i.nodeType === 1) {
				if (i.hasAttributes()) for (let e of i.getAttributeNames()) if (e.endsWith(le)) {
					let t = u[o++], n = i.getAttribute(e).split(y), r = /([.?@])?(.*)/.exec(t);
					c.push({
						type: 1,
						index: a,
						name: r[2],
						strings: n,
						ctor: r[1] === "." ? ke : r[1] === "?" ? Ae : r[1] === "@" ? je : D
					}), i.removeAttribute(e);
				} else e.startsWith(y) && (c.push({
					type: 6,
					index: a
				}), i.removeAttribute(e));
				if (Se.test(i.tagName)) {
					let e = i.textContent.split(y), t = e.length - 1;
					if (t > 0) {
						i.textContent = ce ? ce.emptyScript : "";
						for (let n = 0; n < t; n++) i.append(e[n], b()), Te.nextNode(), c.push({
							type: 2,
							index: ++a
						});
						i.append(e[t], b());
					}
				}
			} else if (i.nodeType === 8) {
				if (i.data === ue) c.push({
					type: 2,
					index: a
				});
				else {
					let e = -1;
					for (; (e = i.data.indexOf(y, e + 1)) !== -1;) c.push({
						type: 7,
						index: a
					}), e += y.length - 1;
				}
			}
			a++;
		}
	}
	static createElement(e, t) {
		let n = fe.createElement("template");
		return n.innerHTML = e, n;
	}
};
function T(e, t, n = e, r) {
	if (t === Ce) return t;
	let i = r === void 0 ? n._$Cl : n._$Co?.[r], a = pe(t) ? void 0 : t._$litDirective$;
	return i?.constructor !== a && (i?._$AO?.(!1), a === void 0 ? i = void 0 : (i = new a(e), i._$AT(e, n, r)), r === void 0 ? n._$Cl = i : (n._$Co ??= [])[r] = i), i !== void 0 && (t = T(e, i._$AS(e, t.values), i, r)), t;
}
var E = class {
	constructor(e, t) {
		this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
	}
	get parentNode() {
		return this._$AM.parentNode;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	u(e) {
		let { el: { content: t }, parts: n } = this._$AD, r = (e?.creationScope ?? fe).importNode(t, !0);
		Te.currentNode = r;
		let i = Te.nextNode(), a = 0, o = 0, s = n[0];
		for (; s !== void 0;) {
			if (a === s.index) {
				let t;
				s.type === 2 ? t = new Oe(i, i.nextSibling, this, e) : s.type === 1 ? t = new s.ctor(i, s.name, s.strings, this, e) : s.type === 6 && (t = new Me(i, this, e)), this._$AV.push(t), s = n[++o];
			}
			a !== s?.index && (i = Te.nextNode(), a++);
		}
		return Te.currentNode = fe, r;
	}
	p(e) {
		let t = 0;
		for (let n of this._$AV) n !== void 0 && (n.strings === void 0 ? n._$AI(e[t]) : (n._$AI(e, n, t), t += n.strings.length - 2)), t++;
	}
}, Oe = class e {
	get _$AU() {
		return this._$AM?._$AU ?? this._$Cv;
	}
	constructor(e, t, n, r) {
		this.type = 2, this._$AH = C, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = n, this.options = r, this._$Cv = r?.isConnected ?? !0;
	}
	get parentNode() {
		let e = this._$AA.parentNode, t = this._$AM;
		return t !== void 0 && e?.nodeType === 11 && (e = t.parentNode), e;
	}
	get startNode() {
		return this._$AA;
	}
	get endNode() {
		return this._$AB;
	}
	_$AI(e, t = this) {
		e = T(this, e, t), pe(e) ? e === C || e == null || e === "" ? (this._$AH !== C && this._$AR(), this._$AH = C) : e !== this._$AH && e !== Ce && this._(e) : e._$litType$ === void 0 ? e.nodeType === void 0 ? he(e) ? this.k(e) : this._(e) : this.T(e) : this.$(e);
	}
	O(e) {
		return this._$AA.parentNode.insertBefore(e, this._$AB);
	}
	T(e) {
		this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
	}
	_(e) {
		this._$AH !== C && pe(this._$AH) ? this._$AA.nextSibling.data = e : this.T(fe.createTextNode(e)), this._$AH = e;
	}
	$(e) {
		let { values: t, _$litType$: n } = e, r = typeof n == "number" ? this._$AC(e) : (n.el === void 0 && (n.el = w.createElement(Ee(n.h, n.h[0]), this.options)), n);
		if (this._$AH?._$AD === r) this._$AH.p(t);
		else {
			let e = new E(r, this), n = e.u(this.options);
			e.p(t), this.T(n), this._$AH = e;
		}
	}
	_$AC(e) {
		let t = we.get(e.strings);
		return t === void 0 && we.set(e.strings, t = new w(e)), t;
	}
	k(t) {
		me(this._$AH) || (this._$AH = [], this._$AR());
		let n = this._$AH, r, i = 0;
		for (let a of t) i === n.length ? n.push(r = new e(this.O(b()), this.O(b()), this, this.options)) : r = n[i], r._$AI(a), i++;
		i < n.length && (this._$AR(r && r._$AB.nextSibling, i), n.length = i);
	}
	_$AR(e = this._$AA.nextSibling, t) {
		for (this._$AP?.(!1, !0, t); e !== this._$AB;) {
			let t = se(e).nextSibling;
			se(e).remove(), e = t;
		}
	}
	setConnected(e) {
		this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
	}
}, D = class {
	get tagName() {
		return this.element.tagName;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	constructor(e, t, n, r, i) {
		this.type = 1, this._$AH = C, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = i, n.length > 2 || n[0] !== "" || n[1] !== "" ? (this._$AH = Array(n.length - 1).fill(/* @__PURE__ */ new String()), this.strings = n) : this._$AH = C;
	}
	_$AI(e, t = this, n, r) {
		let i = this.strings, a = !1;
		if (i === void 0) e = T(this, e, t, 0), a = !pe(e) || e !== this._$AH && e !== Ce, a && (this._$AH = e);
		else {
			let r = e, o, s;
			for (e = i[0], o = 0; o < i.length - 1; o++) s = T(this, r[n + o], t, o), s === Ce && (s = this._$AH[o]), a ||= !pe(s) || s !== this._$AH[o], s === C ? e = C : e !== C && (e += (s ?? "") + i[o + 1]), this._$AH[o] = s;
		}
		a && !r && this.j(e);
	}
	j(e) {
		e === C ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
	}
}, ke = class extends D {
	constructor() {
		super(...arguments), this.type = 3;
	}
	j(e) {
		this.element[this.name] = e === C ? void 0 : e;
	}
}, Ae = class extends D {
	constructor() {
		super(...arguments), this.type = 4;
	}
	j(e) {
		this.element.toggleAttribute(this.name, !!e && e !== C);
	}
}, je = class extends D {
	constructor(e, t, n, r, i) {
		super(e, t, n, r, i), this.type = 5;
	}
	_$AI(e, t = this) {
		if ((e = T(this, e, t, 0) ?? C) === Ce) return;
		let n = this._$AH, r = e === C && n !== C || e.capture !== n.capture || e.once !== n.once || e.passive !== n.passive, i = e !== C && (n === C || r);
		r && this.element.removeEventListener(this.name, this, n), i && this.element.addEventListener(this.name, this, e), this._$AH = e;
	}
	handleEvent(e) {
		typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
	}
}, Me = class {
	constructor(e, t, n) {
		this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = n;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AI(e) {
		T(this, e);
	}
}, Ne = {
	M: le,
	P: y,
	A: ue,
	C: 1,
	L: De,
	R: E,
	D: he,
	V: T,
	I: Oe,
	H: D,
	N: Ae,
	U: je,
	B: ke,
	F: Me
}, Pe = oe.litHtmlPolyfillSupport;
Pe?.(w, Oe), (oe.litHtmlVersions ??= []).push("3.3.3");
var Fe = (e, t, n) => {
	let r = n?.renderBefore ?? t, i = r._$litPart$;
	if (i === void 0) {
		let e = n?.renderBefore ?? null;
		r._$litPart$ = i = new Oe(t.insertBefore(b(), e), e, void 0, n ?? {});
	}
	return i._$AI(e), i;
}, O = globalThis, k = class extends _ {
	constructor() {
		super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
	}
	createRenderRoot() {
		let e = super.createRenderRoot();
		return this.renderOptions.renderBefore ??= e.firstChild, e;
	}
	update(e) {
		let t = this.render();
		this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Fe(t, this.renderRoot, this.renderOptions);
	}
	connectedCallback() {
		super.connectedCallback(), this._$Do?.setConnected(!0);
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this._$Do?.setConnected(!1);
	}
	render() {
		return Ce;
	}
};
k._$litElement$ = !0, k.finalized = !0, O.litElementHydrateSupport?.({ LitElement: k });
var Ie = O.litElementPolyfillSupport;
Ie?.({ LitElement: k }), (O.litElementVersions ??= []).push("4.2.2");
//#endregion
//#region node_modules/@lit/reactive-element/decorators/property.js
var Le = {
	attribute: !0,
	type: String,
	converter: g,
	reflect: !1,
	hasChanged: ie
}, Re = (e = Le, t, n) => {
	let { kind: r, metadata: i } = n, a = globalThis.litPropertyMetadata.get(i);
	if (a === void 0 && globalThis.litPropertyMetadata.set(i, a = /* @__PURE__ */ new Map()), r === "setter" && ((e = Object.create(e)).wrapped = !0), a.set(n.name, e), r === "accessor") {
		let { name: r } = n;
		return {
			set(n) {
				let i = t.get.call(this);
				t.set.call(this, n), this.requestUpdate(r, i, e, !0, n);
			},
			init(t) {
				return t !== void 0 && this.C(r, void 0, e, t), t;
			}
		};
	}
	if (r === "setter") {
		let { name: r } = n;
		return function(n) {
			let i = this[r];
			t.call(this, n), this.requestUpdate(r, i, e, !0, n);
		};
	}
	throw Error("Unsupported decorator location: " + r);
};
function ze(e) {
	return (t, n) => typeof n == "object" ? Re(e, t, n) : ((e, t, n) => {
		let r = t.hasOwnProperty(n);
		return t.constructor.createProperty(n, e), r ? Object.getOwnPropertyDescriptor(t, n) : void 0;
	})(e, t, n);
}
//#endregion
//#region node_modules/@lit/reactive-element/decorators/state.js
function A(e) {
	return ze({
		...e,
		state: !0,
		attribute: !1
	});
}
//#endregion
//#region node_modules/@lit/reactive-element/decorators/base.js
var Be = (e, t, n) => (n.configurable = !0, n.enumerable = !0, Reflect.decorate && typeof t != "object" && Object.defineProperty(e, t, n), n);
//#endregion
//#region node_modules/@lit/reactive-element/decorators/query.js
function Ve(e, t) {
	return (n, r, i) => {
		let a = (t) => t.renderRoot?.querySelector(e) ?? null;
		if (t) {
			let { get: e, set: t } = typeof r == "object" ? n : i ?? (() => {
				let e = Symbol();
				return {
					get() {
						return this[e];
					},
					set(t) {
						this[e] = t;
					}
				};
			})();
			return Be(n, r, { get() {
				let n = e.call(this);
				return n === void 0 && (n = a(this), (n !== null || this.hasUpdated) && t.call(this, n)), n;
			} });
		}
		return Be(n, r, { get() {
			return a(this);
		} });
	};
}
//#endregion
//#region node_modules/lit-html/directive.js
var He = {
	ATTRIBUTE: 1,
	CHILD: 2,
	PROPERTY: 3,
	BOOLEAN_ATTRIBUTE: 4,
	EVENT: 5,
	ELEMENT: 6
}, Ue = (e) => (...t) => ({
	_$litDirective$: e,
	values: t
}), We = class {
	constructor(e) {}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AT(e, t, n) {
		this._$Ct = e, this._$AM = t, this._$Ci = n;
	}
	_$AS(e, t) {
		return this.update(e, t);
	}
	update(e, t) {
		return this.render(...t);
	}
}, Ge = class extends We {
	constructor(e) {
		if (super(e), this.it = C, e.type !== He.CHILD) throw Error(this.constructor.directiveName + "() can only be used in child bindings");
	}
	render(e) {
		if (e === C || e == null) return this._t = void 0, this.it = e;
		if (e === Ce) return e;
		if (typeof e != "string") throw Error(this.constructor.directiveName + "() called with a non-string value");
		if (e === this.it) return this._t;
		this.it = e;
		let t = [e];
		return t.raw = t, this._t = {
			_$litType$: this.constructor.resultType,
			strings: t,
			values: []
		};
	}
};
Ge.directiveName = "unsafeHTML", Ge.resultType = 1;
var Ke = Ue(Ge), { I: qe } = Ne, Je = (e) => e, Ye = () => document.createComment(""), j = (e, t, n) => {
	let r = e._$AA.parentNode, i = t === void 0 ? e._$AB : t._$AA;
	if (n === void 0) n = new qe(r.insertBefore(Ye(), i), r.insertBefore(Ye(), i), e, e.options);
	else {
		let t = n._$AB.nextSibling, a = n._$AM, o = a !== e;
		if (o) {
			let t;
			n._$AQ?.(e), n._$AM = e, n._$AP !== void 0 && (t = e._$AU) !== a._$AU && n._$AP(t);
		}
		if (t !== i || o) {
			let e = n._$AA;
			for (; e !== t;) {
				let t = Je(e).nextSibling;
				Je(r).insertBefore(e, i), e = t;
			}
		}
	}
	return n;
}, Xe = (e, t, n = e) => (e._$AI(t, n), e), Ze = {}, Qe = (e, t = Ze) => e._$AH = t, $e = (e) => e._$AH, et = (e) => {
	e._$AR(), e._$AA.remove();
}, tt = (e, t, n) => {
	let r = /* @__PURE__ */ new Map();
	for (let i = t; i <= n; i++) r.set(e[i], i);
	return r;
}, nt = Ue(class extends We {
	constructor(e) {
		if (super(e), e.type !== He.CHILD) throw Error("repeat() can only be used in text expressions");
	}
	dt(e, t, n) {
		let r;
		n === void 0 ? n = t : t !== void 0 && (r = t);
		let i = [], a = [], o = 0;
		for (let t of e) i[o] = r ? r(t, o) : o, a[o] = n(t, o), o++;
		return {
			values: a,
			keys: i
		};
	}
	render(e, t, n) {
		return this.dt(e, t, n).values;
	}
	update(e, [t, n, r]) {
		let i = $e(e), { values: a, keys: o } = this.dt(t, n, r);
		if (!Array.isArray(i)) return this.ut = o, a;
		let s = this.ut ??= [], c = [], l, u, d = 0, f = i.length - 1, p = 0, m = a.length - 1;
		for (; d <= f && p <= m;) if (i[d] === null) d++;
		else if (i[f] === null) f--;
		else if (s[d] === o[p]) c[p] = Xe(i[d], a[p]), d++, p++;
		else if (s[f] === o[m]) c[m] = Xe(i[f], a[m]), f--, m--;
		else if (s[d] === o[m]) c[m] = Xe(i[d], a[m]), j(e, c[m + 1], i[d]), d++, m--;
		else if (s[f] === o[p]) c[p] = Xe(i[f], a[p]), j(e, i[d], i[f]), f--, p++;
		else if (l === void 0 && (l = tt(o, p, m), u = tt(s, d, f)), l.has(s[d])) {
			if (l.has(s[f])) {
				let t = u.get(o[p]), n = t === void 0 ? null : i[t];
				if (n === null) {
					let t = j(e, i[d]);
					Xe(t, a[p]), c[p] = t;
				} else c[p] = Xe(n, a[p]), j(e, i[d], n), i[t] = null;
				p++;
			} else et(i[f]), f--;
		} else et(i[d]), d++;
		for (; p <= m;) {
			let t = j(e, c[m + 1]);
			Xe(t, a[p]), c[p++] = t;
		}
		for (; d <= f;) {
			let e = i[d++];
			e !== null && et(e);
		}
		return this.ut = o, Qe(e, c), Ce;
	}
});
//#endregion
//#region node_modules/dompurify/dist/purify.es.mjs
function M(e, t) {
	this.v = e, this.k = t;
}
function rt(e, t) {
	(t == null || t > e.length) && (t = e.length);
	for (var n = 0, r = Array(t); n < t; n++) r[n] = e[n];
	return r;
}
function it(e) {
	if (Array.isArray(e)) return e;
}
function at(e, t) {
	var n = e == null ? null : typeof Symbol < "u" && e[Symbol.iterator] || e["@@iterator"];
	if (n != null) {
		var r, i, a, o, s = [], c = !0, l = !1;
		try {
			if (a = (n = n.call(e)).next, t === 0) {
				if (Object(n) !== n) return;
				c = !1;
			} else for (; !(c = (r = a.call(n)).done) && (s.push(r.value), s.length !== t); c = !0);
		} catch (e) {
			l = !0, i = e;
		} finally {
			try {
				if (!c && n.return != null && (o = n.return(), Object(o) !== o)) return;
			} finally {
				if (l) throw i;
			}
		}
		return s;
	}
}
function ot() {
	throw TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
}
function st(e, t) {
	return it(e) || at(e, t) || ct(e, t) || ot();
}
function ct(e, t) {
	if (e) {
		if (typeof e == "string") return rt(e, t);
		var n = {}.toString.call(e).slice(8, -1);
		return n === "Object" && e.constructor && (n = e.constructor.name), n === "Map" || n === "Set" ? Array.from(e) : n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n) ? rt(e, t) : void 0;
	}
}
function lt(e) {
	var t, n;
	function r(t, n) {
		try {
			var a = e[t](n), o = a.value, s = o instanceof M;
			Promise.resolve(s ? o.v : o).then(function(n) {
				if (s) {
					var c = t === "return" && o.k ? t : "next";
					if (!o.k || n.done) return r(c, n);
					n = e[c](n).value;
				}
				i(!!a.done, n);
			}, function(e) {
				r("throw", e);
			});
		} catch (e) {
			i(2, e);
		}
	}
	function i(e, i) {
		e === 2 ? t.reject(i) : t.resolve({
			value: i,
			done: e
		}), (t = t.next) ? r(t.key, t.arg) : n = null;
	}
	this._invoke = function(e, i) {
		return new Promise(function(a, o) {
			var s = {
				key: e,
				arg: i,
				resolve: a,
				reject: o,
				next: null
			};
			n ? n = n.next = s : (t = n = s, r(e, i));
		});
	}, typeof e.return != "function" && (this.return = void 0);
}
lt.prototype[typeof Symbol == "function" && Symbol.asyncIterator || "@@asyncIterator"] = function() {
	return this;
}, lt.prototype.next = function(e) {
	return this._invoke("next", e);
}, lt.prototype.throw = function(e) {
	return this._invoke("throw", e);
}, lt.prototype.return = function(e) {
	return this._invoke("return", e);
};
var ut = Object.entries, dt = Object.setPrototypeOf, ft = Object.isFrozen, pt = Object.getPrototypeOf, mt = Object.getOwnPropertyDescriptor, N = Object.freeze, P = Object.seal, ht = Object.create, F = typeof Reflect < "u" && Reflect, gt = F.apply, _t = F.construct;
N ||= function(e) {
	return e;
}, P ||= function(e) {
	return e;
}, gt ||= function(e, t) {
	var n = [...arguments].slice(2);
	return e.apply(t, n);
}, _t ||= function(e) {
	return new e(...[...arguments].slice(1));
};
var vt = R(Array.prototype.forEach);
Array.prototype.indexOf;
var yt = R(Array.prototype.lastIndexOf), bt = R(Array.prototype.pop), xt = R(Array.prototype.push), St = R(Array.prototype.slice), Ct = R(Array.prototype.splice), wt = Array.isArray, Tt = Bt(Set), Et = R(Set.prototype.add), Dt = R(Set.prototype.has), Ot = R(String.prototype.toLowerCase), kt = R(String.prototype.toString), At = R(String.prototype.match), jt = R(String.prototype.replace), Mt = R(String.prototype.indexOf), Nt = R(String.prototype.trim), Pt = R(Number.prototype.toString), Ft = R(Boolean.prototype.toString), It = typeof BigInt > "u" ? null : R(BigInt.prototype.toString), Lt = typeof Symbol > "u" ? null : R(Symbol.prototype.toString), I = R(Object.prototype.hasOwnProperty), Rt = R(Object.prototype.toString), L = R(RegExp.prototype.test), zt = Bt(TypeError);
function R(e) {
	return function(t) {
		t instanceof RegExp && (t.lastIndex = 0);
		var n = [...arguments].slice(1);
		return gt(e, t, n);
	};
}
function Bt(e) {
	return function() {
		return _t(e, [...arguments]);
	};
}
function z(e, t) {
	let n = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : Ot;
	if (dt && dt(e, null), !wt(t)) return e;
	let r = t.length;
	for (; r--;) {
		let i = t[r];
		if (typeof i == "string") {
			let e = n(i);
			e !== i && (ft(t) || (t[r] = e), i = e);
		}
		e[i] = !0;
	}
	return e;
}
function Vt(e) {
	for (let t = 0; t < e.length; t++) I(e, t) || (e[t] = null);
	return e;
}
function B(e) {
	let t = ht(null);
	for (let r of ut(e)) {
		var n = st(r, 2);
		let i = n[0], a = n[1];
		I(e, i) && (t[i] = wt(a) ? Vt(a) : a && typeof a == "object" && a.constructor === Object ? B(a) : a);
	}
	return t;
}
function Ht(e) {
	switch (typeof e) {
		case "string": return e;
		case "number": return Pt(e);
		case "boolean": return Ft(e);
		case "bigint": return It ? It(e) : "0";
		case "symbol": return Lt ? Lt(e) : "Symbol()";
		case "undefined": return Rt(e);
		case "function":
		case "object": {
			if (e === null) return Rt(e);
			let t = e, n = V(t, "toString");
			if (typeof n == "function") {
				let e = n(t);
				return typeof e == "string" ? e : Rt(e);
			}
			return Rt(e);
		}
		default: return Rt(e);
	}
}
function V(e, t) {
	for (; e !== null;) {
		let n = mt(e, t);
		if (n) {
			if (n.get) return R(n.get);
			if (typeof n.value == "function") return R(n.value);
		}
		e = pt(e);
	}
	function n() {
		return null;
	}
	return n;
}
function Ut(e, t) {
	for (; e !== null;) {
		let n = mt(e, t);
		if (n) return n.get ? R(n.get) : null;
		e = pt(e);
	}
	return null;
}
function Wt(e) {
	try {
		return L(e, ""), !0;
	} catch {
		return !1;
	}
}
var Gt = N(/* @__PURE__ */ "a.abbr.acronym.address.area.article.aside.audio.b.bdi.bdo.big.blink.blockquote.body.br.button.canvas.caption.center.cite.code.col.colgroup.content.data.datalist.dd.decorator.del.details.dfn.dialog.dir.div.dl.dt.element.em.fieldset.figcaption.figure.font.footer.form.h1.h2.h3.h4.h5.h6.head.header.hgroup.hr.html.i.img.input.ins.kbd.label.legend.li.main.map.mark.marquee.menu.menuitem.meter.nav.nobr.ol.optgroup.option.output.p.picture.pre.progress.q.rp.rt.ruby.s.samp.search.section.select.shadow.slot.small.source.spacer.span.strike.strong.style.sub.summary.sup.table.tbody.td.template.textarea.tfoot.th.thead.time.tr.track.tt.u.ul.var.video.wbr".split(".")), Kt = N(/* @__PURE__ */ "svg.a.altglyph.altglyphdef.altglyphitem.animatecolor.animatemotion.animatetransform.circle.clippath.defs.desc.ellipse.enterkeyhint.exportparts.filter.font.g.glyph.glyphref.hkern.image.inputmode.line.lineargradient.marker.mask.metadata.mpath.part.path.pattern.polygon.polyline.radialgradient.rect.stop.style.switch.symbol.text.textpath.title.tref.tspan.view.vkern".split(".")), qt = N([
	"feBlend",
	"feColorMatrix",
	"feComponentTransfer",
	"feComposite",
	"feConvolveMatrix",
	"feDiffuseLighting",
	"feDisplacementMap",
	"feDistantLight",
	"feDropShadow",
	"feFlood",
	"feFuncA",
	"feFuncB",
	"feFuncG",
	"feFuncR",
	"feGaussianBlur",
	"feImage",
	"feMerge",
	"feMergeNode",
	"feMorphology",
	"feOffset",
	"fePointLight",
	"feSpecularLighting",
	"feSpotLight",
	"feTile",
	"feTurbulence"
]), Jt = N([
	"animate",
	"color-profile",
	"cursor",
	"discard",
	"font-face",
	"font-face-format",
	"font-face-name",
	"font-face-src",
	"font-face-uri",
	"foreignobject",
	"hatch",
	"hatchpath",
	"mesh",
	"meshgradient",
	"meshpatch",
	"meshrow",
	"missing-glyph",
	"script",
	"set",
	"solidcolor",
	"unknown",
	"use"
]), Yt = N(/* @__PURE__ */ "math.menclose.merror.mfenced.mfrac.mglyph.mi.mlabeledtr.mmultiscripts.mn.mo.mover.mpadded.mphantom.mroot.mrow.ms.mspace.msqrt.mstyle.msub.msup.msubsup.mtable.mtd.mtext.mtr.munder.munderover.mprescripts".split(".")), Xt = N([
	"maction",
	"maligngroup",
	"malignmark",
	"mlongdiv",
	"mscarries",
	"mscarry",
	"msgroup",
	"mstack",
	"msline",
	"msrow",
	"semantics",
	"annotation",
	"annotation-xml",
	"mprescripts",
	"none"
]), Zt = N(["#text"]), Qt = N(/* @__PURE__ */ "accept.action.align.alt.autocapitalize.autocomplete.autopictureinpicture.autoplay.background.bgcolor.border.capture.cellpadding.cellspacing.checked.cite.class.clear.color.cols.colspan.command.commandfor.controls.controlslist.coords.crossorigin.datetime.decoding.default.dir.disabled.disablepictureinpicture.disableremoteplayback.download.draggable.enctype.enterkeyhint.exportparts.face.for.headers.height.hidden.high.href.hreflang.id.inert.inputmode.integrity.ismap.kind.label.lang.list.loading.loop.low.max.maxlength.media.method.min.minlength.multiple.muted.name.nonce.noshade.novalidate.nowrap.open.optimum.part.pattern.placeholder.playsinline.popover.popovertarget.popovertargetaction.poster.preload.pubdate.radiogroup.readonly.rel.required.rev.reversed.role.rows.rowspan.spellcheck.scope.selected.shape.size.sizes.slot.span.srclang.start.src.srcset.step.style.summary.tabindex.title.translate.type.usemap.valign.value.width.wrap.xmlns".split(".")), $t = N(/* @__PURE__ */ "accent-height.accumulate.additive.alignment-baseline.amplitude.ascent.attributename.attributetype.azimuth.basefrequency.baseline-shift.begin.bias.by.class.clip.clippathunits.clip-path.clip-rule.color.color-interpolation.color-interpolation-filters.color-profile.color-rendering.cx.cy.d.dx.dy.diffuseconstant.direction.display.divisor.dominant-baseline.dur.edgemode.elevation.end.exponent.fill.fill-opacity.fill-rule.filter.filterunits.flood-color.flood-opacity.font-family.font-size.font-size-adjust.font-stretch.font-style.font-variant.font-weight.fx.fy.g1.g2.glyph-name.glyphref.gradientunits.gradienttransform.height.href.id.image-rendering.in.in2.intercept.k.k1.k2.k3.k4.kerning.keypoints.keysplines.keytimes.lang.lengthadjust.letter-spacing.kernelmatrix.kernelunitlength.lighting-color.local.marker-end.marker-mid.marker-start.markerheight.markerunits.markerwidth.maskcontentunits.maskunits.max.mask.mask-type.media.method.mode.min.name.numoctaves.offset.operator.opacity.order.orient.orientation.origin.overflow.paint-order.path.pathlength.patterncontentunits.patterntransform.patternunits.pointer-events.points.preservealpha.preserveaspectratio.primitiveunits.r.rx.ry.radius.refx.refy.repeatcount.repeatdur.restart.result.rotate.scale.seed.shape-rendering.slope.specularconstant.specularexponent.spreadmethod.startoffset.stddeviation.stitchtiles.stop-color.stop-opacity.stroke-dasharray.stroke-dashoffset.stroke-linecap.stroke-linejoin.stroke-miterlimit.stroke-opacity.stroke.stroke-width.style.surfacescale.systemlanguage.tabindex.tablevalues.targetx.targety.transform.transform-origin.text-anchor.text-decoration.text-orientation.text-rendering.textlength.type.u1.u2.unicode.values.vector-effect.viewbox.visibility.version.vert-adv-y.vert-origin-x.vert-origin-y.width.word-spacing.wrap.writing-mode.xchannelselector.ychannelselector.x.x1.x2.xmlns.y.y1.y2.z.zoomandpan".split(".")), en = N(/* @__PURE__ */ "accent.accentunder.align.bevelled.close.columnalign.columnlines.columnspacing.columnspan.denomalign.depth.dir.display.displaystyle.encoding.fence.frame.height.href.id.largeop.length.linethickness.lquote.lspace.mathbackground.mathcolor.mathsize.mathvariant.maxsize.minsize.movablelimits.notation.numalign.open.rowalign.rowlines.rowspacing.rowspan.rspace.rquote.scriptlevel.scriptminsize.scriptsizemultiplier.selection.separator.separators.stretchy.subscriptshift.supscriptshift.symmetric.voffset.width.xmlns".split(".")), tn = N([
	"xlink:href",
	"xml:id",
	"xlink:title",
	"xml:space",
	"xmlns:xlink"
]), nn = P(/{{[\w\W]*|^[\w\W]*}}/g), rn = P(/<%[\w\W]*|^[\w\W]*%>/g), an = P(/\${[\w\W]*/g), on = P(/^data-[\-\w.\u00B7-\uFFFF]+$/), sn = P(/^aria-[\-\w]+$/), cn = P(/^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|matrix):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i), ln = P(/^(?:\w+script|data):/i), un = P(/[\u0000-\u0020\u00A0\u1680\u180E\u2000-\u2029\u205F\u3000]/g), dn = P(/^html$/i), fn = P(/^[a-z][.\w]*(-[.\w]+)+$/i), pn = P(/<[/\w!]/g), mn = P(/<[/\w]/g), hn = P(/<\/no(script|embed|frames)/i), gn = P(/\/>/i), H = {
	element: 1,
	attribute: 2,
	text: 3,
	cdataSection: 4,
	entityReference: 5,
	entityNode: 6,
	processingInstruction: 7,
	comment: 8,
	document: 9,
	documentType: 10,
	documentFragment: 11,
	notation: 12
}, _n = N(z({}, [
	"style",
	"script",
	"xmp",
	"iframe",
	"noembed",
	"noframes",
	"plaintext",
	"noscript"
])), vn = function() {
	return typeof window > "u" ? null : window;
}, yn = function(e, t) {
	if (typeof e != "object" || typeof e.createPolicy != "function") return null;
	let n = null, r = "data-tt-policy-suffix";
	t && t.hasAttribute(r) && (n = t.getAttribute(r));
	let i = "dompurify" + (n ? "#" + n : "");
	try {
		return e.createPolicy(i, {
			createHTML(e) {
				return e;
			},
			createScriptURL(e) {
				return e;
			}
		});
	} catch {
		return console.warn("TrustedTypes policy " + i + " could not be created."), null;
	}
}, bn = function() {
	return {
		afterSanitizeAttributes: [],
		afterSanitizeElements: [],
		afterSanitizeShadowDOM: [],
		beforeSanitizeAttributes: [],
		beforeSanitizeElements: [],
		beforeSanitizeShadowDOM: [],
		uponSanitizeAttribute: [],
		uponSanitizeElement: [],
		uponSanitizeShadowNode: []
	};
}, xn = function(e, t, n, r) {
	return I(e, t) && wt(e[t]) ? z(r.base ? B(r.base) : {}, e[t], r.transform) : n;
}, Sn = function(e, t, n) {
	let r = I(e, t) ? e[t] : void 0;
	return r && typeof r == "object" ? B(r) : n();
};
function Cn() {
	let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : vn(), t = (e) => Cn(e);
	if (t.version = "3.4.17", t.removed = [], !e || !e.document || e.document.nodeType !== H.document || !e.Element) return t.isSupported = !1, t;
	let n = e.document, r = n, i = r.currentScript;
	e.DocumentFragment;
	let a = e.HTMLTemplateElement, o = e.Node, s = e.Element, c = e.NodeFilter;
	e.NamedNodeMap === void 0 && (e.NamedNodeMap || e.MozNamedAttrMap), e.HTMLFormElement;
	let l = e.DOMParser, u = e.trustedTypes, d = s.prototype, f = V(d, "cloneNode"), p = V(d, "remove"), m = V(d, "removeAttributeNode"), h = V(d, "nextSibling"), ee = V(d, "childNodes"), te = V(d, "parentNode"), ne = V(d, "shadowRoot"), re = V(d, "attributes"), g = o && o.prototype ? V(o.prototype, "nodeType") : null, ie = o && o.prototype ? V(o.prototype, "nodeName") : null, ae = o && o.prototype ? V(o.prototype, "ownerDocument") : null, _ = function(e) {
		return g ? g(e) : e.nodeType;
	}, oe = function(e) {
		return ie ? ie(e) : e.nodeName;
	}, se = Ut(d, "namespaceURI"), ce = function(e) {
		return se ? se(e) : e.namespaceURI;
	};
	if (typeof a == "function") {
		let e = n.createElement("template");
		e.content && e.content.ownerDocument && (n = e.content.ownerDocument);
	}
	let v, le = "", y, ue = !1, de = 0, fe = function() {
		if (de > 0) throw zt("A configured TRUSTED_TYPES_POLICY callback (createHTML or createScriptURL) must not call DOMPurify.sanitize, as that causes infinite recursion. Do not pass a policy whose callbacks wrap DOMPurify as TRUSTED_TYPES_POLICY; see the \"DOMPurify and Trusted Types\" section of the README.");
	}, b = function(e) {
		fe(), de++;
		try {
			return v.createHTML(e);
		} finally {
			de--;
		}
	}, pe = function(e) {
		fe(), de++;
		try {
			return v.createScriptURL(e);
		} finally {
			de--;
		}
	}, me = function() {
		return ue ||= (y = yn(u, i), !0), y;
	}, he = n, ge = he.implementation, _e = he.createNodeIterator, ve = he.createDocumentFragment, ye = he.getElementsByTagName, be = r.importNode, x = bn();
	t.isSupported = typeof ut == "function" && typeof te == "function" && ge && ge.createHTMLDocument !== void 0;
	let xe = nn, Se = rn, S = an, Ce = on, C = sn, we = ln, Te = un, Ee = fn, De = cn, w = null, T = z({}, [
		...Gt,
		...Kt,
		...qt,
		...Yt,
		...Zt
	]), E = null, Oe = z({}, [
		...Qt,
		...$t,
		...en,
		...tn
	]), D = Object.seal(ht(null, {
		tagNameCheck: {
			writable: !0,
			configurable: !1,
			enumerable: !0,
			value: null
		},
		attributeNameCheck: {
			writable: !0,
			configurable: !1,
			enumerable: !0,
			value: null
		},
		allowCustomizedBuiltInElements: {
			writable: !0,
			configurable: !1,
			enumerable: !0,
			value: !1
		}
	})), ke = null, Ae = null, je = Object.seal(ht(null, {
		tagCheck: {
			writable: !0,
			configurable: !1,
			enumerable: !0,
			value: null
		},
		attributeCheck: {
			writable: !0,
			configurable: !1,
			enumerable: !0,
			value: null
		}
	})), Me = !0, Ne = !0, Pe = !1, Fe = !0, O = !1, k = !0, Ie = !1, Le = !1, Re = null, ze = null, A = !1, Be = !1, Ve = !1, He = !1, Ue = !0, We = !1, Ge = "user-content-", Ke = !0, qe = !1, Je = null, Ye = {}, j = null, Xe = z({}, /* @__PURE__ */ "annotation-xml.audio.colgroup.desc.foreignobject.head.iframe.math.mi.mn.mo.ms.mtext.noembed.noframes.noscript.plaintext.script.selectedcontent.style.svg.template.thead.title.video.xmp".split(".")), Ze = null, Qe = z({}, [
		"audio",
		"video",
		"img",
		"source",
		"image",
		"track"
	]), $e = null, et = z({}, [
		"alt",
		"class",
		"for",
		"id",
		"label",
		"name",
		"pattern",
		"placeholder",
		"role",
		"summary",
		"title",
		"value",
		"style",
		"xmlns"
	]), tt = "http://www.w3.org/1998/Math/MathML", nt = "http://www.w3.org/2000/svg", M = "http://www.w3.org/1999/xhtml", rt = M, it = !1, at = null, ot = z({}, [
		tt,
		nt,
		M
	], kt), st = N([
		"mi",
		"mo",
		"mn",
		"ms",
		"mtext"
	]), ct = z({}, st), lt = N(["annotation-xml"]), dt = z({}, lt), ft = z({}, [
		"title",
		"style",
		"font",
		"a",
		"script"
	]), pt = null, mt = ["application/xhtml+xml", "text/html"], F = null, gt = null, _t = n.createElement("form"), Pt = function(e) {
		return e instanceof RegExp || e instanceof Function;
	}, Ft = function() {
		let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
		if (gt && gt === e) return;
		(!e || typeof e != "object") && (e = {}), e = B(e), pt = mt.indexOf(e.PARSER_MEDIA_TYPE) === -1 ? "text/html" : e.PARSER_MEDIA_TYPE, F = pt === "application/xhtml+xml" ? kt : Ot, w = xn(e, "ALLOWED_TAGS", T, { transform: F }), E = xn(e, "ALLOWED_ATTR", Oe, { transform: F }), at = xn(e, "ALLOWED_NAMESPACES", ot, { transform: kt }), $e = xn(e, "ADD_URI_SAFE_ATTR", et, {
			transform: F,
			base: et
		}), Ze = xn(e, "ADD_DATA_URI_TAGS", Qe, {
			transform: F,
			base: Qe
		}), j = xn(e, "FORBID_CONTENTS", Xe, { transform: F }), ke = xn(e, "FORBID_TAGS", B({}), { transform: F }), Ae = xn(e, "FORBID_ATTR", B({}), { transform: F }), Ye = I(e, "USE_PROFILES") ? e.USE_PROFILES && typeof e.USE_PROFILES == "object" ? B(e.USE_PROFILES) : e.USE_PROFILES : !1, Me = e.ALLOW_ARIA_ATTR !== !1, Ne = e.ALLOW_DATA_ATTR !== !1, Pe = e.ALLOW_UNKNOWN_PROTOCOLS || !1, Fe = e.ALLOW_SELF_CLOSE_IN_ATTR !== !1, O = e.SAFE_FOR_TEMPLATES || !1, k = e.SAFE_FOR_XML !== !1, Ie = e.WHOLE_DOCUMENT || !1, Be = e.RETURN_DOM || !1, Ve = e.RETURN_DOM_FRAGMENT || !1, He = e.RETURN_TRUSTED_TYPE || !1, A = e.FORCE_BODY || !1, Ue = e.SANITIZE_DOM !== !1, We = e.SANITIZE_NAMED_PROPS || !1, Ke = e.KEEP_CONTENT !== !1, qe = e.IN_PLACE || !1, De = Wt(e.ALLOWED_URI_REGEXP) ? e.ALLOWED_URI_REGEXP : cn, rt = typeof e.NAMESPACE == "string" ? e.NAMESPACE : M, ct = Sn(e, "MATHML_TEXT_INTEGRATION_POINTS", () => z({}, st)), dt = Sn(e, "HTML_INTEGRATION_POINTS", () => z({}, lt));
		let t = Sn(e, "CUSTOM_ELEMENT_HANDLING", () => ht(null));
		if (D = ht(null), I(t, "tagNameCheck") && Pt(t.tagNameCheck) && (D.tagNameCheck = t.tagNameCheck), I(t, "attributeNameCheck") && Pt(t.attributeNameCheck) && (D.attributeNameCheck = t.attributeNameCheck), I(t, "allowCustomizedBuiltInElements") && typeof t.allowCustomizedBuiltInElements == "boolean" && (D.allowCustomizedBuiltInElements = t.allowCustomizedBuiltInElements), P(D), O && (Ne = !1), Ve && (Be = !0), Ye && (w = z({}, Zt), E = ht(null), Ye.html === !0 && (z(w, Gt), z(E, Qt)), Ye.svg === !0 && (z(w, Kt), z(E, $t), z(E, tn)), Ye.svgFilters === !0 && (z(w, qt), z(E, $t), z(E, tn)), Ye.mathMl === !0 && (z(w, Yt), z(E, en), z(E, tn))), je.tagCheck = null, je.attributeCheck = null, I(e, "ADD_TAGS") && (typeof e.ADD_TAGS == "function" ? je.tagCheck = e.ADD_TAGS : wt(e.ADD_TAGS) && (w === T && (w = B(w)), z(w, e.ADD_TAGS, F))), I(e, "ADD_ATTR") && (typeof e.ADD_ATTR == "function" ? je.attributeCheck = e.ADD_ATTR : wt(e.ADD_ATTR) && (E === Oe && (E = B(E)), z(E, e.ADD_ATTR, F))), I(e, "ADD_FORBID_CONTENTS") && wt(e.ADD_FORBID_CONTENTS) && (j === Xe && (j = B(j)), z(j, e.ADD_FORBID_CONTENTS, F)), Ke && (w["#text"] = !0), Ie && z(w, [
			"html",
			"head",
			"body"
		]), w.table && (z(w, ["tbody"]), delete ke.tbody), e.TRUSTED_TYPES_POLICY) {
			if (typeof e.TRUSTED_TYPES_POLICY.createHTML != "function") throw zt("TRUSTED_TYPES_POLICY configuration option must provide a \"createHTML\" hook.");
			if (typeof e.TRUSTED_TYPES_POLICY.createScriptURL != "function") throw zt("TRUSTED_TYPES_POLICY configuration option must provide a \"createScriptURL\" hook.");
			let t = v;
			v = e.TRUSTED_TYPES_POLICY;
			try {
				le = b("");
			} catch (e) {
				throw v = t, e;
			}
		} else e.TRUSTED_TYPES_POLICY === null ? (v = void 0, le = "") : (v === void 0 && (v = me()), v && typeof le == "string" && (le = b("")));
		N && N(e), gt = e;
	}, It = z({}, [
		...Kt,
		...qt,
		...Jt
	]), Lt = z({}, [...Yt, ...Xt]), Rt = function(e, t, n) {
		return t.namespaceURI === M ? e === "svg" : t.namespaceURI === tt ? e === "svg" && (n === "annotation-xml" || ct[n]) : !!It[e];
	}, R = function(e, t, n) {
		return t.namespaceURI === M ? e === "math" : t.namespaceURI === nt ? e === "math" && dt[n] : !!Lt[e];
	}, Bt = function(e, t, n) {
		return t.namespaceURI === nt && !dt[n] || t.namespaceURI === tt && !ct[n] ? !1 : !Lt[e] && (ft[e] || !It[e]);
	}, Vt = function(e) {
		let t = ce(e), n = Ot(oe(e)), r = te(e), i, a;
		return r && _(r) === H.element ? (i = { namespaceURI: ce(r) }, a = Ot(oe(r))) : (i = { namespaceURI: rt }, a = "template"), at[t] ? t === nt ? Rt(n, i, a) : t === tt ? R(n, i, a) : t === M ? Bt(n, i, a) : !!(pt === "application/xhtml+xml" && at[t]) : !1;
	}, wn = function(e) {
		xt(t.removed, { element: e });
		try {
			te(e).removeChild(e);
		} catch {
			if (p(e), !te(e)) throw zt("a node selected for removal could not be detached from its tree and cannot be safely returned; refusing to sanitize in place");
		}
	}, Tn = function(e, t, n) {
		try {
			m(e, t);
		} catch {
			try {
				e.removeAttribute(n);
			} catch {}
		}
	}, U = function(e) {
		W(e);
		let t = ee(e);
		t && vt(St(t), (e) => {
			try {
				p(e);
			} catch {}
		});
		let n = _(e) === H.element ? re(e) : null;
		if (n) for (let t = n.length - 1; t >= 0; --t) {
			let r = n[t], i = r && r.name;
			typeof i == "string" && Tn(e, r, i);
		}
	}, En = function(e, n, r) {
		if (!r) try {
			r = n.getAttributeNode(e);
		} catch {
			r = null;
		}
		xt(t.removed, {
			attribute: r || null,
			from: n
		});
		try {
			r ? m(n, r) : n.removeAttribute(e);
		} catch {
			try {
				n.removeAttribute(e);
			} catch {}
		}
		if (e === "is") {
			if (Be || Ve) try {
				wn(n);
			} catch {}
			else try {
				n.setAttribute(e, "");
			} catch {}
		}
	}, Dn = function(e) {
		let t = re(e);
		if (t) for (let n = t.length - 1; n >= 0; --n) {
			let r = t[n], i = r && r.name;
			typeof i != "string" || E[F(i)] || Tn(e, r, i);
		}
	}, On = function(e, t) {
		let n = arguments.length > 2 && arguments[2] !== void 0 && arguments[2], r = [e];
		for (; r.length > 0;) {
			let e = r.pop();
			if (t(e) === !1) continue;
			if (n && _(e) === H.element) {
				let t = ne(e);
				Hn(t) && r.push(t);
			}
			let i = ee(e);
			if (i) for (let e = i.length - 1; e >= 0; --e) r.push(i[e]);
		}
	}, W = function(e) {
		On(e, (e) => {
			_(e) === H.element && Dn(e);
		});
	}, kn = function(e) {
		let t = [];
		return On(e, (e) => {
			t.push(e);
		}, !0), t;
	}, G = function(e, t) {
		let n = Tt();
		vt(kn(e), (e) => {
			_(e) === H.element && Et(n, e);
		}), vt(t, (e) => {
			_(e) === H.element && !Dt(n, e) && Dn(e);
		});
	}, An = function(e, n) {
		let r = !1;
		return vt(t.removed, (t) => {
			t.element && (r ||= t.element === e, W(t.element));
		}), G(e, n), r;
	}, jn = function(e, t) {
		let n = Je, r = null, i = () => (r || (r = Tt(), vt(t, (e) => {
			Et(r, e);
		})), r);
		for (let t = 0;; t++) {
			let r = kn(e), a = [e], o = !1;
			if (vt(r, (e) => {
				_(e) === H.documentFragment ? xt(a, e) : !o && !Dt(n, e) && (o = Dt(i(), e));
			}), !o) return;
			if (t >= 8) throw zt("the tree kept changing during in-place sanitization; refusing to return it");
			vt(a, (t, n) => {
				Mn(t, n > 0, e, i());
			});
		}
	}, Mn = function(e, t, n, r) {
		let i = Ln(e), a;
		for (; a = i.nextNode();) Dt(r, a) && !Dt(Je, a) && (t && K(x.uponSanitizeShadowNode, a, null), Yn(a, n), nr(a, n), Hn(a.content) && q(a.content));
	}, Nn = function(e) {
		Je && Et(Je, e);
	}, Pn = function(e, t) {
		return k ? e === "patchsrc" || e === "for" && t !== "label" && t !== "output" : !1;
	}, Fn = function(e) {
		k && On(e, (e) => {
			let t = _(e);
			if (t === H.processingInstruction || t === H.comment && L(mn, e.data)) {
				try {
					p(e);
				} catch {}
				return !1;
			}
			if (t === H.element) {
				let t = e, n = F(oe(e));
				try {
					t.hasAttribute && t.hasAttribute("patchsrc") && t.removeAttribute("patchsrc"), t.hasAttribute && t.hasAttribute("for") && Pn("for", n) && t.removeAttribute("for");
				} catch {}
			}
			return !0;
		});
	}, In = function(e) {
		let t = null, r = null;
		if (A) e = "<remove></remove>" + e;
		else {
			let t = At(e, /^[\r\n\t ]+/);
			r = t && t[0];
		}
		pt === "application/xhtml+xml" && rt === M && (e = "<html xmlns=\"http://www.w3.org/1999/xhtml\"><head></head><body>" + e + "</body></html>");
		let i = v ? b(e) : e;
		if (rt === M) try {
			t = new l().parseFromString(i, pt);
		} catch {}
		if (!t || !t.documentElement) {
			t = ge.createDocument(rt, "template", null);
			try {
				t.documentElement.innerHTML = it ? le : i;
			} catch {}
		}
		let a = t.body || t.documentElement;
		return e && r && a.insertBefore(n.createTextNode(r), a.childNodes[0] || null), rt === M ? ye.call(t, Ie ? "html" : "body")[0] : Ie ? t.documentElement : a;
	}, Ln = function(e) {
		let t = ae ? ae(e) : e.ownerDocument;
		return _e.call(t || e, e, c.SHOW_ELEMENT | c.SHOW_COMMENT | c.SHOW_TEXT | c.SHOW_PROCESSING_INSTRUCTION | c.SHOW_CDATA_SECTION, null);
	}, Rn = function(e) {
		return e = jt(e, xe, " "), e = jt(e, Se, " "), e = jt(e, S, " "), e;
	}, zn = function(e) {
		Bn(e);
		let t = e.querySelectorAll?.call(e, "template");
		t && vt(t, (e) => {
			Hn(e.content) && zn(e.content);
		});
	}, Bn = function(e) {
		e.normalize();
		let t = ae ? ae(e) : e.ownerDocument, n = _e.call(t || e, e, c.SHOW_TEXT | c.SHOW_COMMENT | c.SHOW_CDATA_SECTION | c.SHOW_PROCESSING_INSTRUCTION, null), r = n.nextNode();
		for (; r;) r.data = Rn(r.data), r = n.nextNode();
	}, Vn = function(e) {
		let t = ie ? ie(e) : null;
		return typeof t != "string" || F(t) !== "form" ? !1 : typeof e.nodeName != "string" || typeof e.textContent != "string" || typeof e.removeChild != "function" || e.attributes !== re(e) || typeof e.removeAttribute != "function" || typeof e.removeAttributeNode != "function" || typeof e.getAttributeNode != "function" || typeof e.setAttribute != "function" || typeof e.namespaceURI != "string" || typeof e.insertBefore != "function" || typeof e.hasChildNodes != "function" || e.nodeType !== g(e) || e.childNodes !== ee(e);
	}, Hn = function(e) {
		if (!g || typeof e != "object" || !e) return !1;
		try {
			return g(e) === H.documentFragment;
		} catch {
			return !1;
		}
	}, Un = function(e) {
		if (!g || typeof e != "object" || !e) return !1;
		try {
			return typeof g(e) == "number";
		} catch {
			return !1;
		}
	};
	function K(e, n, r) {
		e.length !== 0 && vt(e, (e) => {
			e.call(t, n, r, gt);
		});
	}
	let Wn = function(e, t) {
		return !!(k && e.hasChildNodes() && !Un(e.firstElementChild) && L(pn, e.textContent) && L(pn, e.innerHTML) || k && _n[t] && _(e) === H.element && ce(e) === M && (Un(e.firstElementChild) || typeof e.textContent == "string" && L(pn, e.textContent)) || e.nodeType === H.processingInstruction || k && e.nodeType === H.comment && L(mn, e.data));
	}, Gn = function(e, t) {
		return e instanceof RegExp ? L(e, t) : e instanceof Function && !!e(t, ...[...arguments].slice(2));
	}, Kn = function(e, t, n) {
		if (!ke[t] && Qn(t) && Gn(D.tagNameCheck, t)) return !1;
		if (Ke && !j[t] && !j[Ot(t)]) {
			let t = te(e), r = ee(e);
			if (r && t) {
				let i = r.length;
				for (let a = i - 1; a >= 0; --a) {
					let i = e === n ? f(r[a], !0) : r[a];
					t.insertBefore(i, h(e));
				}
			}
		}
		return wn(e), !0;
	}, qn = function(e, t, n, r) {
		return e.length === 0 ? t : t === n || t === r ? B(t) : t;
	}, Jn = function(e, t) {
		return e === t || te(e) !== null ? !1 : (qe && W(e), !0);
	}, Yn = function(e, n) {
		if (Nn(e), K(x.beforeSanitizeElements, e, null), Jn(e, n)) return !0;
		if (Vn(e)) return wn(e), !0;
		let r = F(oe(e));
		if (w = qn(x.uponSanitizeElement, w, T, Re), K(x.uponSanitizeElement, e, {
			tagName: r,
			allowedTags: w
		}), Jn(e, n)) return !0;
		if (Wn(e, r)) return wn(e), !0;
		if (ke[r] || !(je.tagCheck instanceof Function && je.tagCheck(r)) && !w[r]) {
			let t = Kn(e, r, n);
			return t === !1 && (K(x.afterSanitizeElements, e, null), Jn(e, n)) ? !0 : t;
		}
		if (_(e) === H.element && !Vt(e) || (r === "noscript" || r === "noembed" || r === "noframes") && L(hn, e.innerHTML)) return wn(e), !0;
		if (O && e.nodeType === H.text) {
			let n = Rn(e.textContent);
			e.textContent !== n && (xt(t.removed, { element: e.cloneNode() }), e.textContent = n);
		}
		return K(x.afterSanitizeElements, e, null), Jn(e, n);
	}, Xn = function(e, t, r) {
		if (Ae[t] || Pn(t, e) || Ue && (t === "id" || t === "name") && (r in n || r in _t)) return !1;
		let i = E[t] || je.attributeCheck instanceof Function && je.attributeCheck(t, e);
		return Ne && L(Ce, t) || Me && L(C, t) ? !0 : i ? $e[t] || L(De, jt(r, Te, "")) || (t === "src" || t === "xlink:href" || t === "href") && e !== "script" && Mt(r, "data:") === 0 && Ze[e] || Pe && !L(we, jt(r, Te, "")) ? !0 : !r : Qn(e) && Gn(D.tagNameCheck, e) && Gn(D.attributeNameCheck, t, e) || t === "is" && D.allowCustomizedBuiltInElements && Gn(D.tagNameCheck, r);
	}, Zn = z({}, [
		"annotation-xml",
		"color-profile",
		"font-face",
		"font-face-format",
		"font-face-name",
		"font-face-src",
		"font-face-uri",
		"missing-glyph"
	]), Qn = function(e) {
		return !Zn[Ot(e)] && L(Ee, e);
	}, $n = function(e, t, n, r) {
		if (v && typeof u == "object" && typeof u.getAttributeType == "function" && !n) switch (u.getAttributeType(e, t)) {
			case "TrustedHTML": return b(r);
			case "TrustedScriptURL": return pe(r);
		}
		return r;
	}, er = function(e, t, n, r) {
		try {
			return n ? e.setAttributeNS(n, t, r) : e.setAttribute(t, r), !Vn(e) || (wn(e), !1);
		} catch {
			return En(t, e), !1;
		}
	}, tr = function(e, t) {
		return k && L(/((--!?|])>)|<\/(style|script|title|xmp|textarea|noscript|iframe|noembed|noframes)/i, t) ? !0 : Ot(e) === "attributename" && At(t, "href") !== null;
	}, nr = function(e, n) {
		if (K(x.beforeSanitizeAttributes, e, null), Jn(e, n)) return;
		let r = e.attributes;
		if (!r || Vn(e)) return;
		E = qn(x.uponSanitizeAttribute, E, Oe, ze);
		let i = {
			attrName: "",
			attrValue: "",
			keepAttr: !0,
			allowedAttributes: E,
			forceKeepAttr: void 0
		}, a = r.length, o = F(e.nodeName);
		for (; a--;) {
			let n = r[a], s = n.name, c = n.namespaceURI, l = n.value, u = F(s), d = l, f = s === "value" ? d : Nt(d), p = !1;
			i.attrName = u, i.attrValue = f, i.keepAttr = !0, i.forceKeepAttr = void 0, K(x.uponSanitizeAttribute, e, i), f = i.attrValue, We && (u === "id" || u === "name") && Mt(f, Ge) !== 0 && (En(s, e, n), f = Ge + f, p = !0), tr(s, f) ? En(s, e, n) : i.forceKeepAttr || (i.keepAttr ? !Fe && L(gn, f) ? En(s, e, n) : (O && (f = Rn(f)), Xn(o, u, f) ? (f = $n(o, u, c, f), f !== d && er(e, s, c, f) && p && bt(t.removed)) : En(s, e, n)) : En(s, e, n));
		}
		K(x.afterSanitizeAttributes, e, null), Jn(e, n);
	}, q = function(e) {
		let t = null, n = Ln(e);
		for (K(x.beforeSanitizeShadowDOM, e, null); t = n.nextNode();) if (K(x.uponSanitizeShadowNode, t, null), Yn(t, e), nr(t, e), Hn(t.content) && q(t.content), _(t) === H.element) {
			let e = ne(t);
			Hn(e) && (rr(e), q(e));
		}
		O && Bn(e), K(x.afterSanitizeShadowDOM, e, null);
	}, rr = function(e) {
		let t = [{
			node: e,
			shadow: null
		}];
		for (; t.length > 0;) {
			let e = t.pop();
			if (e.shadow) {
				q(e.shadow);
				continue;
			}
			let n = e.node, r = _(n) === H.element, i = ee(n);
			if (i) for (let e = i.length - 1; e >= 0; --e) t.push({
				node: i[e],
				shadow: null
			});
			if (r) {
				let e = ie ? ie(n) : null;
				if (typeof e == "string" && F(e) === "template") {
					let e = n.content;
					Hn(e) && t.push({
						node: e,
						shadow: null
					});
				}
			}
			if (r) {
				let e = ne(n);
				Hn(e) && t.push({
					node: null,
					shadow: e
				}, {
					node: e,
					shadow: null
				});
			}
		}
	};
	return t.sanitize = function(e) {
		let n = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : {}, i = null, a = null, o = null, s = null;
		if (it = !e, it && (e = "<!-->"), typeof e != "string" && !Un(e) && (e = Ht(e), typeof e != "string")) throw zt("dirty is not a string, aborting");
		if (!t.isSupported) return e;
		Le ? (w = Re, E = ze) : Ft(n), (x.uponSanitizeElement.length > 0 || x.uponSanitizeAttribute.length > 0) && (w = B(w)), x.uponSanitizeAttribute.length > 0 && (E = B(E)), t.removed = [];
		let c = qe && typeof e != "string" && Un(e), l = [], u = Je;
		if (c) {
			Fn(e);
			let t = oe(e);
			if (typeof t == "string") {
				let n = F(t);
				if (!w[n] || ke[n]) throw U(e), zt("root node is forbidden and cannot be sanitized in-place");
			}
			if (Vn(e)) throw U(e), zt("root node is clobbered and cannot be sanitized in-place");
			l = kn(e), Je = Tt();
		} else if (Un(e)) i = In("<!---->"), a = i.ownerDocument.importNode(e, !0), a.nodeType === H.element && a.nodeName === "BODY" || a.nodeName === "HTML" ? i = a : i.appendChild(a), rr(i);
		else {
			if (!Be && !O && !Ie && e.indexOf("<") === -1) return v && He ? b(e) : e;
			if (i = In(e), !i) return Be ? null : He ? le : "";
		}
		i && A && wn(i.firstChild);
		let d = c ? e : i;
		try {
			c && rr(e);
			let t = Ln(d);
			for (; o = t.nextNode();) Yn(o, d), nr(o, d), Hn(o.content) && q(o.content);
			c && jn(e, l);
		} catch (t) {
			throw c && (U(e), An(e, l)), t;
		} finally {
			Je = u;
		}
		if (c) {
			if (An(e, l)) throw zt("a node selected for removal could not be safely returned; refusing to sanitize in place");
			return O && zn(e), e;
		}
		if (Be) {
			if (O && zn(i), Ve) for (s = ve.call(i.ownerDocument); i.firstChild;) s.appendChild(i.firstChild);
			else s = i;
			return (E.shadowroot || E.shadowrootmode) && (s = be.call(r, s, !0)), s;
		}
		let f = Ie ? i.outerHTML : i.innerHTML;
		return Ie && w["!doctype"] && i.ownerDocument && i.ownerDocument.doctype && i.ownerDocument.doctype.name && L(dn, i.ownerDocument.doctype.name) && (f = "<!DOCTYPE " + i.ownerDocument.doctype.name + ">\n" + f), O && (f = Rn(f)), v && He ? b(f) : f;
	}, t.setConfig = function() {
		let e = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
		Ft(e), Le = !0, Re = w, ze = E;
	}, t.clearConfig = function() {
		gt = null, Le = !1, Re = null, ze = null, v = y, le = "";
	}, t.isValidAttribute = function(e, t, n) {
		gt || Ft({});
		let r = F(e), i = F(t);
		return typeof n == "string" && (tr(t, n) || !Fe && L(gn, n)) ? !1 : Xn(r, i, n);
	}, t.addHook = function(e, t) {
		typeof t == "function" && I(x, e) && xt(x[e], t);
	}, t.removeHook = function(e, t) {
		if (I(x, e)) {
			if (t !== void 0) {
				let n = yt(x[e], t);
				return n === -1 ? void 0 : Ct(x[e], n, 1)[0];
			}
			return bt(x[e]);
		}
	}, t.removeHooks = function(e) {
		I(x, e) && (x[e] = []);
	}, t.removeAllHooks = function() {
		x = bn();
	}, t;
}
var wn = Cn();
//#endregion
//#region node_modules/marked/lib/marked.esm.js
function Tn() {
	return {
		async: !1,
		breaks: !1,
		extensions: null,
		gfm: !0,
		hooks: null,
		pedantic: !1,
		renderer: null,
		silent: !1,
		tokenizer: null,
		walkTokens: null
	};
}
var U = Tn();
function En(e) {
	U = e;
}
var Dn = { exec: () => null };
function On(e) {
	let t = [];
	return (n) => {
		let r = Math.max(0, Math.min(3, n - 1)), i = t[r];
		return i || (i = e(r), t[r] = i), i;
	};
}
function W(e, t = "") {
	let n = typeof e == "string" ? e : e.source, r = {
		replace: (e, t) => {
			let i = typeof t == "string" ? t : t.source;
			return i = i.replace(G.caret, "$1"), n = n.replace(e, i), r;
		},
		getRegex: () => new RegExp(n, t)
	};
	return r;
}
var kn = ((e = "") => {
	try {
		return !!RegExp("(?<=1)(?<!1)" + e);
	} catch {
		return !1;
	}
})(), G = {
	codeRemoveIndent: /^(?: {0,3}\t| {1,4})/gm,
	outputLinkReplace: /\\([\[\]])/g,
	indentCodeCompensation: /^(\s+)(?:```)/,
	beginningSpace: /^\s+/,
	endingHash: /#$/,
	startingSpaceChar: /^ /,
	endingSpaceChar: / $/,
	endingSpaceTabChar: /[ \t]$/,
	nonSpaceChar: /[^ ]/,
	newLineCharGlobal: /\n/g,
	tabCharGlobal: /\t/g,
	leadingSpaceTab: /^[ \t]+/,
	multipleSpaceGlobal: /\s+/g,
	blankLine: /^[ \t]*$/,
	doubleBlankLine: /\n[ \t]*\n[ \t]*$/,
	blockquoteStart: /^ {0,3}>/,
	blockquoteSetextReplace: /\n {0,3}((?:=+|-+) *)(?=\n|$)/g,
	blockquoteSetextReplace2: /^ {0,3}>[ \t]?/gm,
	listReplaceNesting: /^ {1,4}(?=( {4})*[^ ])/g,
	listIsTask: /^\[[ xX]\] +\S/,
	listReplaceTask: /^\[[ xX]\] +/,
	listTaskCheckbox: /\[[ xX]\]/,
	anyLine: /\n.*\n/,
	hrefBrackets: /^<(.*)>$/,
	tableDelimiter: /[:|]/,
	tableAlignChars: /^\||\| *$/g,
	tableRowBlankLine: /\n[ \t]*$/,
	tableAlignRight: /^ *-+: *$/,
	tableAlignCenter: /^ *:-+: *$/,
	tableAlignLeft: /^ *:-+ *$/,
	startATag: /^<a /i,
	endATag: /^<\/a>/i,
	startPreScriptTag: /^<(pre|code|kbd|script)(\s|>)/i,
	endPreScriptTag: /^<\/(pre|code|kbd|script)(\s|>)/i,
	startAngleBracket: /^</,
	endAngleBracket: />$/,
	pedanticHrefTitle: /^([^'"]*[^\s])\s+(['"])(.*)\2/,
	unicodeAlphaNumeric: /[\p{L}\p{N}]/u,
	numericCharacterReference: /&#(?:(\d{1,7})|[Xx]([A-Fa-f0-9]{1,6}));/,
	numericCharacterReferenceOrAmpersand: /&#(?:(\d{1,7})|[Xx]([A-Fa-f0-9]{1,6}));|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/g,
	escapeTest: /[&<>"']/,
	escapeReplace: /[&<>"']/g,
	escapeTestNoEncode: /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/,
	escapeReplaceNoEncode: /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/g,
	caret: /(^|[^\[])\^/g,
	percentDecode: /%25/g,
	findPipe: /\|/g,
	splitPipe: / \|/,
	slashPipe: /\\\|/g,
	carriageReturn: /\r\n|\r/g,
	spaceLine: /^ +$/gm,
	notSpaceStart: /^\S*/,
	endingNewline: /\n$/,
	listItemRegex: (e) => RegExp(`^( {0,3}${e})((?:[	 ][^\\n]*)?(?:\\n|$))`),
	nextBulletRegex: On((e) => RegExp(`^ {0,${e}}(?:[*+-]|\\d{1,9}[.)])((?:[ 	][^\\n]*)?(?:\\n|$))`)),
	hrRegex: On((e) => RegExp(`^ {0,${e}}((?:-[ 	]*){3,}|(?:_[ 	]*){3,}|(?:\\*[ 	]*){3,})(?:\\n+|$)`)),
	fencesBeginRegex: On((e) => RegExp(`^ {0,${e}}(?:\`\`\`|~~~)`)),
	headingBeginRegex: On((e) => RegExp(`^ {0,${e}}#`)),
	htmlBeginRegex: On((e) => RegExp(`^ {0,${e}}(?:</?(?:${K})(?: +|$|/?>)|<(?:(?:script|pre|style|textarea)(?:[\\s>]|$)|!--)|<\\?|<![A-Za-z]|<!\\[CDATA\\[)`, "i")),
	blockquoteBeginRegex: On((e) => RegExp(`^ {0,${e}}>`))
}, An = /^(?:[ \t]*(?:\n|$))+/, jn = /^((?: {4}| {0,3}\t)[^\n]+(?:\n(?:[ \t]*(?:\n|$))*)?)+/, Mn = /^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/, Nn = /^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/, Pn = /^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/, Fn = / {0,3}(?:[*+-]|\d{1,9}[.)])/, In = /^(?!bull |blockCode|fences|blockquote|heading|html|table)((?:.|\n(?!\s*?\n|bull |fences|blockquote|heading|hr|html|table))+?)\n {0,3}(=+|-+) *(?:\n+|$)/, Ln = W(In).replace(/bull/g, Fn).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}(?:\s|$)/).replace(/hr/g, / {0,3}(?:(?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/\|table/g, "").getRegex(), Rn = W(In).replace(/bull/g, Fn).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}(?:\s|$)/).replace(/hr/g, / {0,3}(?:(?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/table/g, / {0,3}\|?(?:[:\- ]*\|)+[\:\- ]*\n/).getRegex(), zn = /^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table|[ \t]+\n)[^\n]+)*)/, Bn = /^[^\n]+/, Vn = /(?!\s*\])(?:\\[\s\S]|[^\[\]\\])+/, Hn = W(/^ {0,3}\[(label)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(title))? *(?:\n+|$)/).replace("label", Vn).replace("title", /(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(), Un = W(/^(bull)([ \t][^\n]*?)?(?:\n|$)/).replace(/bull/g, Fn).getRegex(), K = "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul", Wn = /<!--(?:-?>|[\s\S]*?(?:-->|$))/, Gn = W("^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n*|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>[^\\n]*\\n*|$)|<![A-Z][\\s\\S]*?(?:>[^\\n]*\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>[^\\n]*\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|<(?!(?:script|pre|style|textarea)(?![a-z0-9-]))([a-z][a-z0-9-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|</[a-z][a-z0-9-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$))", "i").replace("comment", Wn).replace("tag", K).replace("attribute", / +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(), Kn = (e) => W(zn).replace("hr", Nn).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("|table", "").replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", e).replace("html", " {0,3}(?:</?(?:tag)(?: +|\\n|/?>)|<(?:(?:script|pre|style|textarea)(?:[\\s>]|$)|!--)|<\\?|<![A-Za-z]|<!\\[CDATA\\[)").replace("tag", K).getRegex(), qn = Kn(/ {0,3}(?:[*+-]|1[.)])[ \t]+[^ \t\n]/), Jn = Kn(/ {0,3}(?:[*+-]|\d{1,9}[.)])(?:[ \t]|\n|$)/), Yn = {
	blockquote: W(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace("paragraph", Jn).getRegex(),
	code: jn,
	def: Hn,
	fences: Mn,
	heading: Pn,
	hr: Nn,
	html: Gn,
	lheading: Ln,
	list: Un,
	newline: An,
	paragraph: qn,
	table: Dn,
	text: Bn
}, Xn = W("^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)").replace("hr", Nn).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("blockquote", " {0,3}>").replace("code", "(?: {4}| {0,3}	)[^\\n]").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", " {0,3}(?:[*+-]|1[.)])[ \\t]").replace("html", " {0,3}(?:</?(?:tag)(?: +|\\n|/?>)|<(?:(?:script|pre|style|textarea)(?:[\\s>]|$)|!--)|<\\?|<![A-Za-z]|<!\\[CDATA\\[)").replace("tag", K).getRegex(), Zn = {
	...Yn,
	lheading: Rn,
	table: Xn,
	paragraph: W(zn).replace("hr", Nn).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("table", Xn).replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*(?:\\n|$))|~~~)[^\\n]*(?:\\n|$)").replace("list", " {0,3}(?:[*+-]|1[.)])[ \\t]+[^ \\t\\n]").replace("html", " {0,3}(?:</?(?:tag)(?: +|\\n|/?>)|<(?:(?:script|pre|style|textarea)(?:[\\s>]|$)|!--)|<\\?|<![A-Za-z]|<!\\[CDATA\\[)").replace("tag", K).getRegex()
}, Qn = {
	...Yn,
	html: W("^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:\"[^\"]*\"|'[^']*'|\\s[^'\"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))").replace("comment", Wn).replace(/tag/g, "(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(),
	def: /^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/,
	heading: /^(#{1,6})(.*)(?:\n+|$)/,
	fences: Dn,
	lheading: /^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/,
	paragraph: W(zn).replace("hr", Nn).replace("heading", " *#{1,6} *[^\n]").replace("lheading", Ln).replace("|table", "").replace("blockquote", " {0,3}>").replace("|fences", "").replace("|list", "").replace("|html", "").replace("|tag", "").getRegex()
}, $n = /^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/, er = /^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/, tr = /^( {2,}|\\)\n(?!\s*$)[ \t]*/, nr = /^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/, q = /[\p{P}\p{S}]/u, rr = /[\s\p{P}\p{S}]/u, ir = /[^\s\p{P}\p{S}]/u, ar = W(/^((?![*_])punctSpace)/, "u").replace(/punctSpace/g, rr).getRegex(), or = /[\p{Pi}\p{Ps}"']/u, sr = /(?!~)[\p{P}\p{S}]/u, cr = /(?!~)[\s\p{P}\p{S}]/u, lr = /(?:[^\s\p{P}\p{S}]|~)/u, ur = W(/link|precode-code|html/, "g").replace("link", /\[(?:[^\[\]`]|(?<a>`+)[^`]+\k<a>(?!`))*?\]\((?:\\[\s\S]|[^\\\(\)]|\((?:\\[\s\S]|[^\\\(\)])*\))*\)/).replace("precode-", kn ? "(?<!`)()" : "(^^|[^`])").replace("code", /(?<b>`+)[^`]+\k<b>(?!`)/).replace("html", /<(?! )[^<>]*?>/).getRegex(), dr = /^(?:\*+(?:((?!\*)punct)|([^\s*]))?)|^_+(?:((?!_)punct)|([^\s_]))?/, fr = W(dr, "u").replace(/punct/g, q).getRegex(), pr = W(dr, "u").replace(/punct/g, sr).getRegex(), mr = W(/^(?:\*+(?:((?!\*)(?!openQuote)punct)|([^\s*]))?)|^_+(?:((?!_)(?!openQuote)punct)|([^\s_]))?/, "u").replace(/openQuote/g, or).replace(/punct/g, q).getRegex(), hr = "^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)punctSpace(\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|notPunctSpace(\\*+)(?=notPunctSpace)", gr = W(hr, "gu").replace(/notPunctSpace/g, ir).replace(/punctSpace/g, rr).replace(/punct/g, q).getRegex(), _r = W(hr, "gu").replace(/notPunctSpace/g, lr).replace(/punctSpace/g, cr).replace(/punct/g, sr).getRegex(), vr = W("^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)[\\s](\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|(?:(?!\\*)punct|notPunctSpace)(\\*+)(?!\\*)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, ir).replace(/punctSpace/g, rr).replace(/punct/g, q).getRegex(), yr = W("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)punctSpace(_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)", "gu").replace(/notPunctSpace/g, ir).replace(/punctSpace/g, rr).replace(/punct/g, q).getRegex(), br = W("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)[\\s](_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)|(?:(?!_)punct|notPunctSpace)(_+)(?!_)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, ir).replace(/punctSpace/g, rr).replace(/punct/g, q).getRegex(), xr = W(/^~~?(?:((?!~)punct)|[^\s~])/, "u").replace(/punct/g, q).getRegex(), Sr = W("^[^~]+(?=[^~])|(?!~)punct(~~?)(?=[\\s]|$)|notPunctSpace(~~?)(?!~)(?=punctSpace|$)|(?!~)punctSpace(~~?)(?=notPunctSpace)|[\\s](~~?)(?!~)(?=punct)|(?!~)punct(~~?)(?!~)(?=punct)|notPunctSpace(~~?)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, ir).replace(/punctSpace/g, rr).replace(/punct/g, q).getRegex(), Cr = W(/\\(punct)/, "gu").replace(/punct/g, q).getRegex(), wr = W(/(`+)(?:[^`]|[^`][\s\S]*?[^`])\1(?!`)|`+|\\(punct)/, "gu").replace(/punct/g, q).getRegex(), Tr = W(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace("scheme", /[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace("email", /[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(), Er = W(Wn).replace("(?:-->|$)", "-->").getRegex(), Dr = W("^comment|^</[a-zA-Z][a-zA-Z0-9-]*\\s*>|^<[a-zA-Z][a-zA-Z0-9-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>").replace("comment", Er).replace("attribute", /\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(), Or = /\[(?:\\[\s\S]|[^\[\]\\])*\]/, kr = W(/(?:\[(?:brackets|\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+(?!`)[^`]*?`+(?!`)|``+(?=\])|[^\[\]\\`])*?/).replace("brackets", Or).getRegex(), Ar = W(/^!?\[(label)\]\([ \t\n]*(href)(?:(?:[ \t]+(?:\n[ \t]*)?|\n[ \t]*)(title))?[ \t\n]*\)/).replace("label", kr).replace("href", /<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]+|(?=\))/).replace("title", /"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(), jr = W(/^!?\[(label)\]\[(ref)\]/).replace("label", kr).replace("ref", Vn).getRegex(), Mr = W(/^!?\[(ref)\](?:\[\])?/).replace("ref", Vn).getRegex(), Nr = /(?!\s*\])(?:\\[\s\S]|[^\[\]\\]){1,999}/, Pr = W(/(?:[^\[\]\\`]*(?:\[(?:brackets|\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+(?!`)[^`]*?`+(?!`)|``+(?=\]))){0,999}?[^\[\]\\`]*?/).replace("brackets", Or).getRegex(), Fr = W("reflink|nolink(?!\\()", "g").replace("reflink", W(/^!?\[(label)\]\[(ref)\]/).replace("label", Pr).replace("ref", Nr).getRegex()).replace("nolink", W(/^!?\[(ref)\](?:\[\])?/).replace("ref", Nr).getRegex()).getRegex(), Ir = /[hH][tT][tT][pP][sS]?|[fF][tT][pP]/, Lr = W(/(?:mailto:email|xmpp:email(?:\/[A-Za-z0-9@.]+)?)/).replace(/email/g, /[A-Za-z0-9._+-]+@[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![\w-])/).getRegex(), Rr = {
	_backpedal: Dn,
	anyPunctuation: Cr,
	anyPunctuationOutsideCode: wr,
	autolink: Tr,
	blockSkip: ur,
	br: tr,
	code: er,
	del: Dn,
	delLDelim: Dn,
	delRDelim: Dn,
	emStrongLDelim: fr,
	emStrongRDelimAst: gr,
	emStrongRDelimUnd: yr,
	escape: $n,
	link: Ar,
	nolink: Mr,
	punctuation: ar,
	reflink: jr,
	reflinkSearch: Fr,
	tag: Dr,
	text: nr,
	url: Dn
}, zr = {
	...Rr,
	emStrongLDelim: mr,
	emStrongRDelimAst: vr,
	emStrongRDelimUnd: br,
	link: W(/^!?\[(label)\]\((.*?)\)/).replace("label", kr).getRegex(),
	reflink: W(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label", kr).getRegex()
}, Br = {
	...Rr,
	emStrongRDelimAst: _r,
	emStrongLDelim: pr,
	delLDelim: xr,
	delRDelim: Sr,
	url: W(/^emailProtocol|^((?:protocol):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/).replace("emailProtocol", Lr).replace("protocol", Ir).replace("email", /[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![\w-])/).getRegex(),
	_backpedal: /(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/,
	del: /^(~~?)(?=[^\s~])((?:\\[\s\S]|[^\\])*?(?:\\[\s\S]|[^\s~\\]))\1(?=[^~]|$)/,
	text: W(/^(?:[^a-zA-Z0-9](?=emailProtocol)|(`+|~+|[^`~])(?:(?=[`~])|(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|protocol:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9](?=emailProtocol)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@))))/).replace("protocol", Ir).replace(/emailProtocol/g, /(?:mailto|xmpp):/).getRegex()
}, Vr = {
	...Br,
	br: W(tr).replace("{2,}", "*").getRegex(),
	text: W(Br.text).replace("\\b_", "\\b_| {2,}\\n").replace(/\{2,\}/g, "*").getRegex()
}, Hr = {
	normal: Yn,
	gfm: Zn,
	pedantic: Qn
}, Ur = {
	normal: Rr,
	gfm: Br,
	breaks: Vr,
	pedantic: zr
}, Wr = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	"\"": "&quot;",
	"'": "&#39;"
}, Gr = (e) => Wr[e];
function J(e, t) {
	if (t) {
		if (G.escapeTest.test(e)) return e.replace(G.escapeReplace, Gr);
	} else if (G.escapeTestNoEncode.test(e)) return e.replace(G.escapeReplaceNoEncode, Gr);
	return e;
}
function Kr(e) {
	return G.numericCharacterReference.test(e) ? e.replace(G.numericCharacterReferenceOrAmpersand, (e, t, n) => {
		if (t === void 0 && n === void 0) return "&amp;";
		let r = t === void 0 ? Number.parseInt(n, 16) : Number.parseInt(t, 10);
		return r === 0 || r > 1114111 || r >= 55296 && r <= 57343 ? "�" : r === 38 ? "&amp;" : String.fromCodePoint(r);
	}) : e;
}
function qr(e) {
	try {
		e = encodeURI(e).replace(G.percentDecode, "%");
	} catch {
		return null;
	}
	return e;
}
function Jr(e, t) {
	let n = e.replace(G.findPipe, (e, t, n) => {
		let r = !1, i = t;
		for (; --i >= 0 && n[i] === "\\";) r = !r;
		return r ? "|" : " |";
	}).split(G.splitPipe), r = 0;
	if (n[0].trim() || n.shift(), n.length > 0 && !n.at(-1)?.trim() && n.pop(), t) {
		if (n.length > t) n.splice(t);
		else for (; n.length < t;) n.push("");
	}
	for (; r < n.length; r++) n[r] = n[r].trim().replace(G.slashPipe, "|");
	return n;
}
function Yr(e, t, n) {
	let r = e.length;
	if (r === 0) return "";
	let i = 0;
	for (; i < r;) {
		let a = e.charAt(r - i - 1);
		if (a === t && !n) i++;
		else if (a !== t && n) i++;
		else break;
	}
	return e.slice(0, r - i);
}
function Xr(e) {
	let t = e.split("\n"), n = t.length - 1;
	for (; n >= 0 && G.blankLine.test(t[n]);) n--;
	return t.length - n <= 2 ? e : t.slice(0, n + 1).join("\n");
}
function Zr(e) {
	return e.trim().toLowerCase().toUpperCase().toLowerCase();
}
function Qr(e, t) {
	if (e.indexOf(t[0]) === -1 && e.indexOf(t[1]) === -1) return -1;
	let n = 0;
	for (let r = 0; r < e.length; r++) if (e[r] === "\\") r++;
	else if (e[r] === t[0]) n++;
	else if (e[r] === t[1] && (n--, n < 0)) return r;
	return n > 0 ? -2 : -1;
}
function $r(e, t = 0) {
	let n = t, r = "";
	for (let t of e) if (t === "	") {
		let e = 4 - n % 4;
		r += " ".repeat(e), n += e;
	} else r += t, n++;
	return r;
}
function ei(e, t, n, r, i) {
	let a = t.href, o = t.title || null, s = e[1].replace(i.other.outputLinkReplace, "$1"), c = e[0].charAt(0) === "!", l = r.state.inLink, u = r.state.linkEmitted, d = r.state.inRawBlock;
	r.state.inLink = !0, r.state.linkEmitted = !1;
	let f = r.inlineTokens(s), p = r.state.linkEmitted;
	if (r.state.linkEmitted = u, r.state.inLink = l, !c) {
		if (p) {
			r.state.inRawBlock = d;
			return;
		}
		r.state.linkEmitted = !0;
	}
	return {
		type: c ? "image" : "link",
		raw: n,
		href: a,
		title: o,
		text: s,
		tokens: f
	};
}
function ti(e, t, n) {
	let r = e.match(n.other.indentCodeCompensation);
	if (r === null) return t;
	let i = r[1];
	return t.split("\n").map((e) => {
		let t = e.match(n.other.beginningSpace);
		if (t === null) return e;
		let [r] = t;
		return e.slice(Math.min(r.length, i.length));
	}).join("\n");
}
function ni(e, t, n, r) {
	if (!t.includes("<")) return !1;
	for (let i = 0; i < t.length; i++) {
		if (t[i] === "\\") {
			i++;
			continue;
		}
		if (t[i] === "`") {
			let e = r.inline.code.exec(t.slice(i));
			if (e) {
				i += e[0].length - 1;
				continue;
			}
		}
		if (t[i] !== "<") continue;
		let a = e.slice(n + i), o = r.inline.tag.exec(a) || r.inline.autolink.exec(a);
		if (o) {
			if (o[0].length > t.length - i) return !0;
			i += o[0].length - 1;
		}
	}
	return !1;
}
var ri = class {
	options;
	rules;
	lexer;
	constructor(e) {
		this.options = e || U;
	}
	space(e) {
		let t = this.rules.block.newline.exec(e);
		if (t && t[0].length > 0) return {
			type: "space",
			raw: t[0]
		};
	}
	code(e) {
		let t = this.rules.block.code.exec(e);
		if (t) {
			let e = this.options.pedantic ? t[0] : Xr(t[0]);
			return {
				type: "code",
				raw: e,
				codeBlockStyle: "indented",
				text: e.replace(this.rules.other.codeRemoveIndent, "")
			};
		}
	}
	fences(e) {
		let t = this.rules.block.fences.exec(e);
		if (t) {
			let e = t[0], n = ti(e, t[3] || "", this.rules);
			return {
				type: "code",
				raw: e,
				lang: t[2] ? t[2].trim().replace(this.rules.inline.anyPunctuation, "$1") : t[2],
				text: n
			};
		}
	}
	heading(e) {
		let t = this.rules.block.heading.exec(e);
		if (t) {
			let e = t[2].trim();
			if (this.rules.other.endingHash.test(e)) {
				let t = Yr(e, "#");
				(this.options.pedantic || !t || this.rules.other.endingSpaceTabChar.test(t)) && (e = t.trim());
			}
			return {
				type: "heading",
				raw: Yr(t[0], "\n"),
				depth: t[1].length,
				text: e,
				tokens: this.lexer.inline(e)
			};
		}
	}
	hr(e) {
		let t = this.rules.block.hr.exec(e);
		if (t) return {
			type: "hr",
			raw: Yr(t[0], "\n")
		};
	}
	blockquote(e) {
		let t = this.rules.block.blockquote.exec(e);
		if (t) {
			let e = Yr(t[0], "\n").split("\n"), n = "", r = "", i = [];
			for (; e.length > 0;) {
				let t = !1, a = [], o = 0;
				for (; o < e.length; o++) if (this.rules.other.blockquoteStart.test(e[o])) a.push(e[o]), t = !0;
				else if (!t) a.push(e[o]);
				else break;
				e = e.slice(o);
				let s = a.join("\n"), c = s.replace(this.rules.other.blockquoteSetextReplace, "\n    $1").replace(this.rules.other.blockquoteSetextReplace2, "");
				n = n ? `${n}
${s}` : s, r = r ? `${r}
${c}` : c;
				let l = this.lexer.state.top;
				if (this.lexer.state.top = !0, this.lexer.blockTokens(c, i, !0), this.lexer.state.top = l, e.length === 0) break;
				let u = i.at(-1);
				if (u?.type === "code" || u?.type === "heading" || u?.type === "hr" || u?.type === "html") break;
				if (u?.type === "blockquote") {
					let t = u, a = e.join("\n"), o = t.raw + "\n" + a.replace(this.rules.other.blockquoteSetextReplace2, ""), s = this.blockquote(o);
					i[i.length - 1] = s;
					let c = o.substring(s.raw.length).replace(/^\n/, ""), l = c ? c.split("\n").length : 0, d = l ? e.slice(0, -l) : e;
					d.length > 0 && (n = `${n}
${d.join("\n")}`), r = r.substring(0, r.length - t.text.length) + s.text;
					break;
				}
				if (u?.type === "list") {
					let t = u, a = t.raw + "\n" + e.join("\n"), o = this.list(a);
					i[i.length - 1] = o, n = n.substring(0, n.length - u.raw.length) + o.raw, r = r.substring(0, r.length - t.raw.length) + o.raw, e = a.substring(i.at(-1).raw.length).split("\n");
				}
			}
			return {
				type: "blockquote",
				raw: n,
				tokens: i,
				text: r
			};
		}
	}
	list(e) {
		let t = this.rules.block.list.exec(e);
		if (t) {
			let n = e, r = () => n.length - e.length, i = t[1].trim(), a = i.length > 1, o = {
				type: "list",
				raw: "",
				ordered: a,
				start: a ? +i.slice(0, -1) : "",
				loose: !1,
				items: []
			};
			i = a ? `\\d{1,9}\\${i.slice(-1)}` : `\\${i}`, this.options.pedantic && (i = a ? i : "[*+-]");
			let s = this.rules.other.listItemRegex(i), c = !1;
			for (; e;) {
				let i = !1, a = "";
				if (!(t = s.exec(e)) || this.rules.block.hr.test(e)) break;
				let l = r();
				e = e.substring(t[0].length);
				let u = t[2].split("\n", 1)[0], d = t[1].length, f = this.options.pedantic ? $r(u, d) : u.replace(this.rules.other.leadingSpaceTab, (e) => $r(e, d)), p = e.split("\n", 1)[0], m = !f.trim(), h = 0;
				if (this.options.pedantic ? (h = 2, a = f.trimStart()) : m ? h = d + 1 : (h = f.search(this.rules.other.nonSpaceChar), h = h > 4 ? 1 : h, a = f.slice(h), h += d), m && this.rules.other.blankLine.test(p) && (e = e.substring(p.length + 1), i = !0), !i) {
					let t = this.rules.other.nextBulletRegex(h), n = this.rules.other.hrRegex(h), r = this.rules.other.fencesBeginRegex(h), i = this.rules.other.headingBeginRegex(h), o = this.rules.other.htmlBeginRegex(h), s = this.rules.other.blockquoteBeginRegex(h);
					for (; e;) {
						let c = e.split("\n", 1)[0], l;
						if (p = c, this.options.pedantic ? (p = p.replace(this.rules.other.listReplaceNesting, "  "), l = p) : l = p.replace(this.rules.other.leadingSpaceTab, (e) => $r(e)), r.test(p) || i.test(p) || o.test(p) || s.test(p) || t.test(p) || n.test(p)) break;
						if (l.search(this.rules.other.nonSpaceChar) >= h || !p.trim()) a += "\n" + l.slice(h);
						else {
							if (m || f.replace(this.rules.other.tabCharGlobal, "    ").search(this.rules.other.nonSpaceChar) >= 4 || r.test(f) || i.test(f) || n.test(f)) break;
							a += "\n" + p;
						}
						m = !p.trim(), e = e.substring(c.length + 1), f = l.slice(h);
					}
				}
				let ee = n.slice(l, r());
				o.loose || (c ? o.loose = !0 : this.rules.other.doubleBlankLine.test(ee) && (c = !0)), o.items.push({
					type: "list_item",
					raw: ee,
					task: !!this.options.gfm && this.rules.other.listIsTask.test(a),
					loose: !1,
					text: a,
					tokens: []
				});
			}
			let l = o.items.at(-1);
			if (l) l.raw = l.raw.trimEnd(), l.text = l.text.trimEnd();
			else return;
			o.raw = n.slice(0, r()).trimEnd();
			for (let e of o.items) if (this.lexer.state.top = !1, e.tokens = this.lexer.blockTokens(e.text, []), !o.loose) {
				let t = e.tokens.filter((e) => e.type === "space");
				o.loose = t.length > 0 && t.some((e) => this.rules.other.anyLine.test(e.raw));
			}
			for (let e of o.items) {
				let t = e.tokens[0];
				if (e.task && (t?.type === "text" || t?.type === "paragraph")) {
					e.text = e.text.replace(this.rules.other.listReplaceTask, ""), t.raw = t.raw.replace(this.rules.other.listReplaceTask, ""), t.text = t.text.replace(this.rules.other.listReplaceTask, "");
					for (let e = this.lexer.inlineQueue.length - 1; e >= 0; e--) if (this.rules.other.listIsTask.test(this.lexer.inlineQueue[e].src)) {
						this.lexer.inlineQueue[e].src = this.lexer.inlineQueue[e].src.replace(this.rules.other.listReplaceTask, "");
						break;
					}
					let n = this.rules.other.listTaskCheckbox.exec(e.raw);
					if (n) {
						let t = {
							type: "checkbox",
							raw: n[0] + " ",
							checked: n[0] !== "[ ]"
						};
						e.checked = t.checked, o.loose ? e.tokens[0] && ["paragraph", "text"].includes(e.tokens[0].type) && "tokens" in e.tokens[0] && e.tokens[0].tokens ? (e.tokens[0].raw = t.raw + e.tokens[0].raw, e.tokens[0].text = t.raw + e.tokens[0].text, e.tokens[0].tokens.unshift(t)) : e.tokens.unshift({
							type: "paragraph",
							raw: t.raw,
							text: t.raw,
							tokens: [t]
						}) : e.tokens.unshift(t);
					}
				} else e.task &&= !1;
			}
			if (o.loose) for (let e of o.items) {
				e.loose = !0;
				for (let t of e.tokens) t.type === "text" && (t.type = "paragraph");
			}
			return o;
		}
	}
	html(e) {
		let t = this.rules.block.html.exec(e);
		if (t) {
			let e = Xr(t[0]);
			return {
				type: "html",
				block: !0,
				raw: e,
				pre: t[1] === "pre" || t[1] === "script" || t[1] === "style",
				text: e
			};
		}
	}
	def(e) {
		let t = this.rules.block.def.exec(e);
		if (t) {
			if (!this.rules.other.startAngleBracket.test(t[2]) && Qr(t[2], "()") !== -1) return;
			let e = Zr(t[1]).replace(this.rules.other.multipleSpaceGlobal, " "), n = t[2] ? t[2].replace(this.rules.other.hrefBrackets, "$1").replace(this.rules.inline.anyPunctuation, "$1") : "", r = t[3] ? t[3].substring(1, t[3].length - 1).replace(this.rules.inline.anyPunctuation, "$1") : t[3];
			return {
				type: "def",
				tag: e,
				raw: Yr(t[0], "\n"),
				href: n,
				title: r
			};
		}
	}
	table(e) {
		let t = this.rules.block.table.exec(e);
		if (!t || !this.rules.other.tableDelimiter.test(t[2])) return;
		let n = Jr(t[1]), r = t[2].replace(this.rules.other.tableAlignChars, "").split("|"), i = t[3]?.trim() ? t[3].replace(this.rules.other.tableRowBlankLine, "").split("\n") : [], a = {
			type: "table",
			raw: Yr(t[0], "\n"),
			header: [],
			align: [],
			rows: []
		};
		if (n.length === r.length) {
			for (let e of r) this.rules.other.tableAlignRight.test(e) ? a.align.push("right") : this.rules.other.tableAlignCenter.test(e) ? a.align.push("center") : this.rules.other.tableAlignLeft.test(e) ? a.align.push("left") : a.align.push(null);
			for (let e = 0; e < n.length; e++) a.header.push({
				text: n[e],
				tokens: this.lexer.inline(n[e]),
				header: !0,
				align: a.align[e]
			});
			for (let e of i) a.rows.push(Jr(e, a.header.length).map((e, t) => ({
				text: e,
				tokens: this.lexer.inline(e),
				header: !1,
				align: a.align[t]
			})));
			return a;
		}
	}
	lheading(e) {
		let t = this.rules.block.lheading.exec(e);
		if (t) {
			let e = t[1].trim();
			return {
				type: "heading",
				raw: Yr(t[0], "\n"),
				depth: t[2].charAt(0) === "=" ? 1 : 2,
				text: e,
				tokens: this.lexer.inline(e)
			};
		}
	}
	paragraph(e) {
		let t = this.rules.block.paragraph.exec(e);
		if (t) {
			let e = t[1].charAt(t[1].length - 1) === "\n" ? t[1].slice(0, -1) : t[1];
			return {
				type: "paragraph",
				raw: t[0],
				text: e,
				tokens: this.lexer.inline(e)
			};
		}
	}
	text(e) {
		let t = this.rules.block.text.exec(e);
		if (t) return {
			type: "text",
			raw: t[0],
			text: t[0],
			tokens: this.lexer.inline(t[0])
		};
	}
	escape(e) {
		let t = this.rules.inline.escape.exec(e);
		if (t) return {
			type: "escape",
			raw: t[0],
			text: t[1]
		};
	}
	tag(e) {
		let t = this.rules.inline.tag.exec(e);
		if (t) return !this.lexer.state.inLink && this.rules.other.startATag.test(t[0]) ? this.lexer.state.inLink = !0 : this.lexer.state.inLink && this.rules.other.endATag.test(t[0]) && (this.lexer.state.inLink = !1), !this.lexer.state.inRawBlock && this.rules.other.startPreScriptTag.test(t[0]) ? this.lexer.state.inRawBlock = !0 : this.lexer.state.inRawBlock && this.rules.other.endPreScriptTag.test(t[0]) && (this.lexer.state.inRawBlock = !1), {
			type: "html",
			raw: t[0],
			inLink: this.lexer.state.inLink,
			inRawBlock: this.lexer.state.inRawBlock,
			block: !1,
			text: t[0]
		};
	}
	link(e) {
		if (this.lexer.state.linkParenPossible === !1) return;
		let t = this.rules.inline.link.exec(e);
		if (t) {
			let n = t[0].charAt(0) === "!" ? 2 : 1;
			if (!this.options.pedantic && ni(e, t[1], n, this.rules)) return;
			let r = t[2].trim();
			if (!this.options.pedantic && this.rules.other.startAngleBracket.test(r)) {
				if (!this.rules.other.endAngleBracket.test(r)) return;
				let e = Yr(r.slice(0, -1), "\\");
				if ((r.length - e.length) % 2 == 0) return;
			} else {
				let e = Qr(t[2], "()");
				if (e === -2) return;
				if (e > -1) {
					let n = (t[0].indexOf("!") === 0 ? 5 : 4) + t[1].length + e;
					t[2] = t[2].substring(0, e), t[0] = t[0].substring(0, n).trim(), t[3] = "";
				}
			}
			let i = t[2], a = "";
			if (this.options.pedantic) {
				let e = this.rules.other.pedanticHrefTitle.exec(i);
				e && (i = e[1], a = e[3]);
			} else a = t[3] ? t[3].slice(1, -1) : "";
			return i = i.trim(), this.rules.other.startAngleBracket.test(i) && (i = this.options.pedantic && !this.rules.other.endAngleBracket.test(r) ? i.slice(1) : i.slice(1, -1)), ei(t, {
				href: i && i.replace(this.rules.inline.anyPunctuation, "$1"),
				title: a && a.replace(this.rules.inline.anyPunctuation, "$1")
			}, t[0], this.lexer, this.rules);
		}
	}
	reflink(e, t) {
		let n;
		if ((n = this.rules.inline.reflink.exec(e)) || (n = this.rules.inline.nolink.exec(e))) {
			let r = n[0].charAt(0) === "!" ? 2 : 1;
			if (!this.options.pedantic && ni(e, n[1], r, this.rules)) return;
			let i = t[Zr((n[2] || n[1]).replace(this.rules.other.multipleSpaceGlobal, " "))];
			if (!i) {
				let e = n[0].charAt(0);
				return {
					type: "text",
					raw: e,
					text: e
				};
			}
			return ei(n, i, n[0], this.lexer, this.rules);
		}
	}
	emStrong(e, t, n = "") {
		let r = this.rules.inline.emStrongLDelim.exec(e);
		if (!(!r || !r[1] && !r[2] && !r[3] && !r[4] || r[4] && n.match(this.rules.other.unicodeAlphaNumeric)) && (!(r[1] || r[3]) || !n || this.rules.inline.punctuation.exec(n))) {
			let i = [...r[0]].length - 1, a, o, s = i, c = 0, l = r[0][0], u = n === l, d = l === "*" ? this.rules.inline.emStrongRDelimAst : this.rules.inline.emStrongRDelimUnd;
			for (d.lastIndex = 0, t = t.slice(-1 * e.length + i); (r = d.exec(t)) !== null;) {
				if (a = r[1] || r[2] || r[3] || r[4] || r[5] || r[6], !a) continue;
				if (o = [...a].length, r[3] || r[4]) {
					s += o;
					continue;
				}
				if (r[5] || r[6]) {
					if (i % 3 && !((i + o) % 3)) {
						c += o;
						continue;
					}
					if (u) break;
				}
				if (s -= o, s > 0) continue;
				o = Math.min(o, o + s + c);
				let t = [...r[0]][0].length, n = e.slice(0, i + r.index + t + o);
				if (Math.min(i, o) % 2) {
					let e = n.slice(1, -1);
					return {
						type: "em",
						raw: n,
						text: e,
						tokens: this.lexer.inlineTokens(e)
					};
				}
				let l = n.slice(2, -2);
				return {
					type: "strong",
					raw: n,
					text: l,
					tokens: this.lexer.inlineTokens(l)
				};
			}
		}
	}
	codespan(e) {
		let t = this.rules.inline.code.exec(e);
		if (t) {
			let e = t[2].replace(this.rules.other.newLineCharGlobal, " "), n = this.rules.other.nonSpaceChar.test(e), r = this.rules.other.startingSpaceChar.test(e) && this.rules.other.endingSpaceChar.test(e);
			return n && r && (e = e.substring(1, e.length - 1)), {
				type: "codespan",
				raw: t[0],
				text: e
			};
		}
	}
	br(e) {
		let t = this.rules.inline.br.exec(e);
		if (t) return {
			type: "br",
			raw: t[0]
		};
	}
	del(e, t, n = "") {
		let r = this.rules.inline.delLDelim.exec(e);
		if (r && (!r[1] || !n || this.rules.inline.punctuation.exec(n))) {
			let n = [...r[0]].length - 1, i, a, o = n, s = this.rules.inline.delRDelim;
			for (s.lastIndex = 0, t = t.slice(-1 * e.length + n); (r = s.exec(t)) !== null;) {
				if (i = r[1] || r[2] || r[3] || r[4] || r[5] || r[6], !i || (a = [...i].length, a !== n)) continue;
				if (r[3] || r[4]) {
					o += a;
					continue;
				}
				if (o -= a, o > 0) continue;
				a = Math.min(a, a + o);
				let t = [...r[0]][0].length, s = e.slice(0, n + r.index + t + a), c = s.slice(n, -n);
				return {
					type: "del",
					raw: s,
					text: c,
					tokens: this.lexer.inlineTokens(c)
				};
			}
		}
	}
	autolink(e) {
		let t = this.rules.inline.autolink.exec(e);
		if (t) {
			let e, n;
			return t[2] === "@" ? (e = t[1], n = "mailto:" + e) : (e = t[1], n = e), {
				type: "link",
				raw: t[0],
				text: e,
				href: n,
				autolink: !0,
				tokens: [{
					type: "text",
					raw: e,
					text: e
				}]
			};
		}
	}
	url(e) {
		let t;
		if (t = this.rules.inline.url.exec(e)) {
			let e, n;
			if (t[2] === "@") e = t[0], n = "mailto:" + e;
			else {
				let r;
				do
					r = t[0], t[0] = this.rules.inline._backpedal.exec(t[0])?.[0] ?? "";
				while (r !== t[0]);
				e = t[0], n = t[1] === "www." ? "http://" + t[0] : t[0];
			}
			return {
				type: "link",
				raw: t[0],
				text: e,
				href: n,
				autolink: !0,
				tokens: [{
					type: "text",
					raw: e,
					text: e
				}]
			};
		}
	}
	inlineText(e) {
		let t = this.rules.inline.text.exec(e);
		if (t) {
			let e = this.lexer.state.inRawBlock;
			return {
				type: "text",
				raw: t[0],
				text: e ? t[0] : Kr(t[0]),
				escaped: e
			};
		}
	}
}, Y = class e {
	tokens;
	options;
	state;
	inlineQueue;
	tokenizer;
	constructor(e) {
		this.tokens = [], this.tokens.links = Object.create(null), this.options = e || U, this.options.tokenizer = this.options.tokenizer || new ri(), this.tokenizer = this.options.tokenizer, this.tokenizer.options = this.options, this.tokenizer.lexer = this, this.inlineQueue = [], this.state = {
			inLink: !1,
			inRawBlock: !1,
			linkEmitted: !1,
			linkParenPossible: !0,
			top: !0
		};
		let t = {
			other: G,
			block: Hr.normal,
			inline: Ur.normal
		};
		this.options.pedantic ? (t.block = Hr.pedantic, t.inline = Ur.pedantic) : this.options.gfm && (t.block = Hr.gfm, t.inline = this.options.breaks ? Ur.breaks : Ur.gfm), this.tokenizer.rules = t;
	}
	static get rules() {
		return {
			block: Hr,
			inline: Ur
		};
	}
	static lex(t, n) {
		return new e(n).lex(t);
	}
	static lexInline(t, n) {
		return new e(n).inlineTokens(t);
	}
	lex(e) {
		e = e.replace(G.carriageReturn, "\n"), this.blockTokens(e, this.tokens);
		for (let e = 0; e < this.inlineQueue.length; e++) {
			let t = this.inlineQueue[e];
			this.inlineTokens(t.src, t.tokens);
		}
		return this.inlineQueue = [], this.tokens;
	}
	blockTokens(e, t = [], n = !1) {
		this.tokenizer.lexer = this, this.options.pedantic && (e = e.replace(G.tabCharGlobal, "    ").replace(G.spaceLine, ""));
		let r = 1 / 0;
		for (; e;) {
			if (e.length < r) r = e.length;
			else {
				this.infiniteLoopError(e.charCodeAt(0));
				break;
			}
			let i;
			if (this.options.extensions?.block?.some((n) => (i = n.call({ lexer: this }, e, t)) ? (e = e.substring(i.raw.length), t.push(i), !0) : !1)) continue;
			if (i = this.tokenizer.space(e)) {
				e = e.substring(i.raw.length);
				let n = t.at(-1);
				i.raw.length === 1 && n !== void 0 ? n.raw += "\n" : t.push(i);
				continue;
			}
			if (i = this.tokenizer.code(e)) {
				e = e.substring(i.raw.length);
				let n = t.at(-1);
				n?.type === "paragraph" || n?.type === "text" ? (n.raw += (n.raw.endsWith("\n") ? "" : "\n") + i.raw, n.text += "\n" + i.text, this.inlineQueue.at(-1).src = n.text) : t.push(i);
				continue;
			}
			if ((i = this.tokenizer.fences(e)) || (i = this.tokenizer.heading(e)) || (i = this.tokenizer.hr(e)) || (i = this.tokenizer.blockquote(e)) || (i = this.tokenizer.list(e)) || (i = this.tokenizer.html(e))) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.def(e)) {
				e = e.substring(i.raw.length);
				let n = t.at(-1);
				n?.type === "paragraph" || n?.type === "text" ? (n.raw += (n.raw.endsWith("\n") ? "" : "\n") + i.raw, n.text += "\n" + i.raw, this.inlineQueue.at(-1).src = n.text) : this.tokens.links[i.tag] || (this.tokens.links[i.tag] = {
					href: i.href,
					title: i.title
				}, t.push(i));
				continue;
			}
			if ((i = this.tokenizer.table(e)) || (i = this.tokenizer.lheading(e))) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			let a = e;
			if (this.options.extensions?.startBlock) {
				let t = 1 / 0, n = e.slice(1), r;
				this.options.extensions.startBlock.forEach((e) => {
					r = e.call({ lexer: this }, n), typeof r == "number" && r >= 0 && (t = Math.min(t, r));
				}), t < 1 / 0 && t >= 0 && (a = e.substring(0, t + 1));
			}
			if (this.state.top && (i = this.tokenizer.paragraph(a))) {
				let r = t.at(-1);
				n && r?.type === "paragraph" ? (r.raw += (r.raw.endsWith("\n") ? "" : "\n") + i.raw, r.text += "\n" + i.text, this.inlineQueue.pop(), this.inlineQueue.at(-1).src = r.text) : t.push(i), n = a.length !== e.length, e = e.substring(i.raw.length);
			} else if (i = this.tokenizer.text(e)) {
				e = e.substring(i.raw.length);
				let n = t.at(-1);
				n?.type === "text" ? (n.raw += (n.raw.endsWith("\n") ? "" : "\n") + i.raw, n.text += "\n" + i.text, this.inlineQueue.pop(), this.inlineQueue.at(-1).src = n.text) : t.push(i);
			} else if (e) {
				this.infiniteLoopError(e.charCodeAt(0));
				break;
			}
		}
		return this.state.top = !0, t;
	}
	inline(e, t = []) {
		return this.inlineQueue.push({
			src: e,
			tokens: t
		}), t;
	}
	linkInText(e) {
		if (!e.includes("[")) return !1;
		let t = this.tokenizer.rules.inline.link;
		for (let n of e.matchAll(this.tokenizer.rules.inline.blockSkip)) if (t.test(n[0]) && e.charAt(n.index - 1) !== "!") return !0;
		for (let t of e.matchAll(this.tokenizer.rules.inline.reflinkSearch)) {
			let e = t[0], n = e.lastIndexOf("[");
			if (e.charAt(0) !== "!" && Object.hasOwn(this.tokens.links, Zr(e.slice(n + 1, -1))) && !(n > 1 && this.linkInText(e.slice(1, n - 1)))) return !0;
		}
		return !1;
	}
	inlineTokens(e, t = []) {
		this.tokenizer.lexer = this;
		let n = this.state.linkParenPossible;
		this.state.linkParenPossible = n && e.includes(")");
		try {
			return this.#e(e, t);
		} finally {
			this.state.linkParenPossible = n;
		}
	}
	#e(e, t) {
		let n = e;
		if (this.tokens.links && e.includes("[")) {
			let e = this.tokenizer.rules.inline.reflinkSearch, t = (n) => {
				let r = n.lastIndexOf("[");
				if (!Object.hasOwn(this.tokens.links, Zr(n.slice(r + 1, -1)))) return n;
				if (r > 1 && n.charAt(0) !== "!") {
					let i = n.slice(1, r - 1);
					if (this.linkInText(i)) return "[" + i.replace(e, t) + "][" + "a".repeat(n.length - r - 2) + "]";
				}
				return "[" + "a".repeat(n.length - 2) + "]";
			};
			n = n.replace(e, t);
		}
		n = n.replace(this.tokenizer.rules.inline.anyPunctuationOutsideCode, (e, t, n) => n ? "+".repeat(e.length) : t ? t + e.slice(t.length, -t.length).replace(/`/g, "+") + t : e), n = n.replace(this.tokenizer.rules.inline.blockSkip, (e, t, n) => {
			let r = n ? n.length : 0;
			return e.slice(0, r) + "[" + "a".repeat(e.length - r - 2) + "]";
		}), n = this.options.hooks?.emStrongMask?.call({ lexer: this }, n) ?? n;
		let r = !1, i = "", a = 1 / 0;
		for (; e;) {
			if (e.length < a) a = e.length;
			else {
				this.infiniteLoopError(e.charCodeAt(0));
				break;
			}
			r || (i = ""), r = !1;
			let o;
			if (this.options.extensions?.inline?.some((n) => (o = n.call({ lexer: this }, e, t)) ? (e = e.substring(o.raw.length), t.push(o), !0) : !1)) continue;
			if ((o = this.tokenizer.escape(e)) || (o = this.tokenizer.tag(e)) || (o = this.tokenizer.link(e))) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.reflink(e, this.tokens.links)) {
				e = e.substring(o.raw.length);
				let n = t.at(-1);
				o.type === "text" && n?.type === "text" ? (n.raw += o.raw, n.text += o.text) : t.push(o);
				continue;
			}
			if ((o = this.tokenizer.emStrong(e, n, i)) || (o = this.tokenizer.codespan(e)) || (o = this.tokenizer.br(e)) || (o = this.tokenizer.del(e, n, i)) || (o = this.tokenizer.autolink(e)) || !this.state.inLink && (o = this.tokenizer.url(e))) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			let s = e;
			if (this.options.extensions?.startInline) {
				let t = 1 / 0, n = e.slice(1), r;
				this.options.extensions.startInline.forEach((e) => {
					r = e.call({ lexer: this }, n), typeof r == "number" && r >= 0 && (t = Math.min(t, r));
				}), t < 1 / 0 && t >= 0 && (s = e.substring(0, t + 1));
			}
			if (o = this.tokenizer.inlineText(s)) {
				e = e.substring(o.raw.length), o.raw.slice(-1) !== "_" && (i = o.raw.slice(-1)), r = !0;
				let n = t.at(-1);
				n?.type === "text" ? (n.raw += o.raw, n.text += o.text) : t.push(o);
			} else if (e) {
				this.infiniteLoopError(e.charCodeAt(0));
				break;
			}
		}
		return t;
	}
	infiniteLoopError(e) {
		let t = "Infinite loop on byte: " + e;
		if (this.options.silent) console.error(t);
		else throw Error(t);
	}
}, ii = class {
	options;
	parser;
	constructor(e) {
		this.options = e || U;
	}
	space(e) {
		return "";
	}
	code({ text: e, lang: t, escaped: n }) {
		let r = (t || "").match(G.notSpaceStart)?.[0], i = e ? e.replace(G.endingNewline, "") + "\n" : "";
		return r ? "<pre><code class=\"language-" + J(r) + "\">" + (n ? i : J(i, !0)) + "</code></pre>\n" : "<pre><code>" + (n ? i : J(i, !0)) + "</code></pre>\n";
	}
	blockquote({ tokens: e }) {
		return `<blockquote>
${this.parser.parse(e)}</blockquote>
`;
	}
	html({ text: e }) {
		return e;
	}
	def(e) {
		return "";
	}
	heading({ tokens: e, depth: t }) {
		return `<h${t}>${this.parser.parseInline(e)}</h${t}>
`;
	}
	hr(e) {
		return "<hr>\n";
	}
	list(e) {
		let t = e.ordered, n = e.start, r = "";
		for (let t = 0; t < e.items.length; t++) {
			let n = e.items[t];
			r += this.listitem(n);
		}
		let i = t ? "ol" : "ul", a = t && n !== 1 ? " start=\"" + n + "\"" : "";
		return "<" + i + a + ">\n" + r + "</" + i + ">\n";
	}
	listitem(e) {
		return `<li>${this.parser.parse(e.tokens)}</li>
`;
	}
	checkbox({ checked: e }) {
		return "<input " + (e ? "checked=\"\" " : "") + "disabled=\"\" type=\"checkbox\"> ";
	}
	paragraph({ tokens: e }) {
		return `<p>${this.parser.parseInline(e)}</p>
`;
	}
	table(e) {
		let t = "", n = "";
		for (let t = 0; t < e.header.length; t++) n += this.tablecell(e.header[t]);
		t += this.tablerow({ text: n });
		let r = "";
		for (let t = 0; t < e.rows.length; t++) {
			let i = e.rows[t];
			n = "";
			for (let e = 0; e < i.length; e++) n += this.tablecell(i[e]);
			r += this.tablerow({ text: n });
		}
		return r &&= `<tbody>${r}</tbody>`, "<table>\n<thead>\n" + t + "</thead>\n" + r + "</table>\n";
	}
	tablerow({ text: e }) {
		return `<tr>
${e}</tr>
`;
	}
	tablecell(e) {
		let t = this.parser.parseInline(e.tokens), n = e.header ? "th" : "td";
		return (e.align ? `<${n} align="${e.align}">` : `<${n}>`) + t + `</${n}>
`;
	}
	strong({ tokens: e }) {
		return `<strong>${this.parser.parseInline(e)}</strong>`;
	}
	em({ tokens: e }) {
		return `<em>${this.parser.parseInline(e)}</em>`;
	}
	codespan({ text: e }) {
		return `<code>${J(e, !0)}</code>`;
	}
	br(e) {
		return "<br>";
	}
	del({ tokens: e }) {
		return `<del>${this.parser.parseInline(e)}</del>`;
	}
	link({ href: e, title: t, text: n, tokens: r, autolink: i }) {
		let a = i ? J(n, !0) : this.parser.parseInline(r), o = qr(e);
		if (o === null) return a;
		e = J(o, i);
		let s = "<a href=\"" + e + "\"";
		return t && (s += " title=\"" + J(t) + "\""), s += ">" + a + "</a>", s;
	}
	image({ href: e, title: t, text: n, tokens: r }) {
		r && (n = this.parser.parseInline(r, this.parser.textRenderer));
		let i = qr(e);
		if (i === null) return J(n);
		e = i;
		let a = `<img src="${J(e)}" alt="${J(n)}"`;
		return t && (a += ` title="${J(t)}"`), a += ">", a;
	}
	text(e) {
		return "tokens" in e && e.tokens ? this.parser.parseInline(e.tokens) : "escaped" in e && e.escaped ? e.text : J(e.text);
	}
}, ai = class {
	strong({ text: e }) {
		return e;
	}
	em({ text: e }) {
		return e;
	}
	codespan({ text: e }) {
		return e;
	}
	del({ text: e }) {
		return e;
	}
	html({ text: e }) {
		return e;
	}
	text({ text: e }) {
		return e;
	}
	link({ text: e }) {
		return "" + e;
	}
	image({ text: e }) {
		return "" + e;
	}
	br() {
		return "";
	}
	checkbox({ raw: e }) {
		return e;
	}
}, X = class e {
	options;
	renderer;
	textRenderer;
	constructor(e) {
		this.options = e || U, this.options.renderer = this.options.renderer || new ii(), this.renderer = this.options.renderer, this.renderer.options = this.options, this.renderer.parser = this, this.textRenderer = new ai();
	}
	static parse(t, n) {
		return new e(n).parse(t);
	}
	static parseInline(t, n) {
		return new e(n).parseInline(t);
	}
	parse(e) {
		this.renderer.parser = this;
		let t = "";
		for (let n = 0; n < e.length; n++) {
			let r = e[n];
			if (this.options.extensions?.renderers?.[r.type]) {
				let e = r, n = this.options.extensions.renderers[e.type].call({ parser: this }, e);
				if (n !== !1 || ![
					"space",
					"hr",
					"heading",
					"code",
					"table",
					"blockquote",
					"list",
					"checkbox",
					"html",
					"def",
					"paragraph",
					"text"
				].includes(e.type)) {
					t += n || "";
					continue;
				}
			}
			let i = r;
			switch (i.type) {
				case "space":
					t += this.renderer.space(i);
					break;
				case "hr":
					t += this.renderer.hr(i);
					break;
				case "heading":
					t += this.renderer.heading(i);
					break;
				case "code":
					t += this.renderer.code(i);
					break;
				case "table":
					t += this.renderer.table(i);
					break;
				case "blockquote":
					t += this.renderer.blockquote(i);
					break;
				case "list":
					t += this.renderer.list(i);
					break;
				case "checkbox":
					t += this.renderer.checkbox(i);
					break;
				case "html":
					t += this.renderer.html(i);
					break;
				case "def":
					t += this.renderer.def(i);
					break;
				case "paragraph":
					t += this.renderer.paragraph(i);
					break;
				case "text":
					t += this.renderer.text(i);
					break;
				default: {
					let e = "Token with \"" + i.type + "\" type was not found.";
					if (this.options.silent) return console.error(e), "";
					throw Error(e);
				}
			}
		}
		return t;
	}
	parseInline(e, t = this.renderer) {
		this.renderer.parser = this;
		let n = "";
		for (let r = 0; r < e.length; r++) {
			let i = e[r];
			if (this.options.extensions?.renderers?.[i.type]) {
				let e = this.options.extensions.renderers[i.type].call({ parser: this }, i);
				if (e !== !1 || ![
					"escape",
					"html",
					"link",
					"image",
					"checkbox",
					"strong",
					"em",
					"codespan",
					"br",
					"del",
					"text"
				].includes(i.type)) {
					n += e || "";
					continue;
				}
			}
			let a = i;
			switch (a.type) {
				case "escape":
					n += t.text(a);
					break;
				case "html":
					n += t.html(a);
					break;
				case "link":
					n += t.link(a);
					break;
				case "image":
					n += t.image(a);
					break;
				case "checkbox":
					n += t.checkbox(a);
					break;
				case "strong":
					n += t.strong(a);
					break;
				case "em":
					n += t.em(a);
					break;
				case "codespan":
					n += t.codespan(a);
					break;
				case "br":
					n += t.br(a);
					break;
				case "del":
					n += t.del(a);
					break;
				case "text":
					n += t.text(a);
					break;
				default: {
					let e = "Token with \"" + a.type + "\" type was not found.";
					if (this.options.silent) return console.error(e), "";
					throw Error(e);
				}
			}
		}
		return n;
	}
}, oi = class {
	options;
	block;
	constructor(e) {
		this.options = e || U;
	}
	static passThroughHooks = /* @__PURE__ */ new Set([
		"preprocess",
		"postprocess",
		"processAllTokens",
		"emStrongMask"
	]);
	static passThroughHooksRespectAsync = /* @__PURE__ */ new Set([
		"preprocess",
		"postprocess",
		"processAllTokens"
	]);
	preprocess(e) {
		return e;
	}
	postprocess(e) {
		return e;
	}
	processAllTokens(e) {
		return e;
	}
	emStrongMask(e) {
		return e;
	}
	provideLexer(e = this.block) {
		return e ? Y.lex : Y.lexInline;
	}
	provideParser(e = this.block) {
		return e ? X.parse : X.parseInline;
	}
};
function si(e, t) {
	if (Array.isArray(t)) for (let n = 0; n < t.length; n++) e.push(t[n]);
	else e.push(t);
}
var ci = class {
	defaults = Tn();
	options = this.setOptions;
	parse = this.parseMarkdown(!0);
	parseInline = this.parseMarkdown(!1);
	Parser = X;
	Renderer = ii;
	TextRenderer = ai;
	Lexer = Y;
	Tokenizer = ri;
	Hooks = oi;
	constructor(...e) {
		this.use(...e);
	}
	walkTokens(e, t) {
		let n = [];
		for (let r of e) switch (si(n, t.call(this, r)), r.type) {
			case "table": {
				let e = r;
				for (let r of e.header) si(n, this.walkTokens(r.tokens, t));
				for (let r of e.rows) for (let e of r) si(n, this.walkTokens(e.tokens, t));
				break;
			}
			case "list": {
				let e = r;
				si(n, this.walkTokens(e.items, t));
				break;
			}
			default: {
				let e = r;
				this.defaults.extensions?.childTokens?.[e.type] ? this.defaults.extensions.childTokens[e.type].forEach((r) => {
					let i = e[r].flat(1 / 0);
					si(n, this.walkTokens(i, t));
				}) : e.tokens && si(n, this.walkTokens(e.tokens, t));
			}
		}
		return n;
	}
	use(...e) {
		let t = this.defaults.extensions || {
			renderers: {},
			childTokens: {}
		};
		return e.forEach((e) => {
			let n = { ...e };
			if (n.async = this.defaults.async || n.async || !1, e.extensions && (e.extensions.forEach((e) => {
				if (!e.name) throw Error("extension name required");
				if ("renderer" in e) {
					let n = t.renderers[e.name];
					n ? t.renderers[e.name] = function(...t) {
						let r = e.renderer.apply(this, t);
						return r === !1 && (r = n.apply(this, t)), r;
					} : t.renderers[e.name] = e.renderer;
				}
				if ("tokenizer" in e) {
					if (!e.level || e.level !== "block" && e.level !== "inline") throw Error("extension level must be 'block' or 'inline'");
					let n = t[e.level];
					n ? n.unshift(e.tokenizer) : t[e.level] = [e.tokenizer], e.start && (e.level === "block" ? t.startBlock ? t.startBlock.push(e.start) : t.startBlock = [e.start] : e.level === "inline" && (t.startInline ? t.startInline.push(e.start) : t.startInline = [e.start]));
				}
				"childTokens" in e && e.childTokens && (t.childTokens[e.name] = e.childTokens);
			}), n.extensions = t), e.renderer) {
				let t = this.defaults.renderer || new ii(this.defaults);
				for (let n in e.renderer) {
					if (!(n in t)) throw Error(`renderer '${n}' does not exist`);
					if (["options", "parser"].includes(n)) continue;
					let r = n, i = e.renderer[r], a = t[r];
					t[r] = (...e) => {
						let n = i.apply(t, e);
						return n === !1 && (n = a.apply(t, e)), n || "";
					};
				}
				n.renderer = t;
			}
			if (e.tokenizer) {
				let t = this.defaults.tokenizer || new ri(this.defaults);
				for (let n in e.tokenizer) {
					if (!(n in t)) throw Error(`tokenizer '${n}' does not exist`);
					if ([
						"options",
						"rules",
						"lexer"
					].includes(n)) continue;
					let r = n, i = e.tokenizer[r], a = t[r];
					t[r] = (...e) => {
						let n = i.apply(t, e);
						return n === !1 && (n = a.apply(t, e)), n;
					};
				}
				n.tokenizer = t;
			}
			if (e.hooks) {
				let t = this.defaults.hooks || new oi();
				for (let n in e.hooks) {
					if (!(n in t)) throw Error(`hook '${n}' does not exist`);
					if (["options", "block"].includes(n)) continue;
					let r = n, i = e.hooks[r], a = t[r];
					t[r] = oi.passThroughHooks.has(n) ? (e) => {
						if (this.defaults.async && oi.passThroughHooksRespectAsync.has(n)) return (async () => {
							let n = await i.call(t, e);
							return a.call(t, n);
						})();
						let r = i.call(t, e);
						return a.call(t, r);
					} : (...e) => {
						if (this.defaults.async) return (async () => {
							let n = await i.apply(t, e);
							return n === !1 && (n = await a.apply(t, e)), n;
						})();
						let n = i.apply(t, e);
						return n === !1 && (n = a.apply(t, e)), n;
					};
				}
				n.hooks = t;
			}
			if (e.walkTokens) {
				let t = this.defaults.walkTokens, r = e.walkTokens;
				n.walkTokens = function(e) {
					let n = [];
					return n.push(r.call(this, e)), t && si(n, t.call(this, e)), n;
				};
			}
			this.defaults = {
				...this.defaults,
				...n
			};
		}), this;
	}
	setOptions(e) {
		return this.defaults = {
			...this.defaults,
			...e
		}, this;
	}
	lexer(e, t) {
		return Y.lex(e, t ?? this.defaults);
	}
	parser(e, t) {
		return X.parse(e, t ?? this.defaults);
	}
	parseMarkdown(e) {
		return (t, n) => {
			let r = { ...n }, i = {
				...this.defaults,
				...r
			}, a = this.onError(!!i.silent, !!i.async);
			if (this.defaults.async === !0 && r.async === !1) return a(/* @__PURE__ */ Error("marked(): The async option was set to true by an extension. Remove async: false from the parse options object to return a Promise."));
			if (typeof t > "u" || t === null) return a(/* @__PURE__ */ Error("marked(): input parameter is undefined or null"));
			if (typeof t != "string") return a(/* @__PURE__ */ Error("marked(): input parameter is of type " + Object.prototype.toString.call(t) + ", string expected"));
			if (i.hooks && (i.hooks.options = i, i.hooks.block = e), i.async) return (async () => {
				let n = i.hooks ? await i.hooks.preprocess(t) : t, r = await (i.hooks ? await i.hooks.provideLexer(e) : e ? Y.lex : Y.lexInline)(n, i), a = i.hooks ? await i.hooks.processAllTokens(r) : r;
				i.walkTokens && await Promise.all(this.walkTokens(a, i.walkTokens));
				let o = await (i.hooks ? await i.hooks.provideParser(e) : e ? X.parse : X.parseInline)(a, i);
				return i.hooks ? await i.hooks.postprocess(o) : o;
			})().catch(a);
			try {
				i.hooks && (t = i.hooks.preprocess(t));
				let n = (i.hooks ? i.hooks.provideLexer(e) : e ? Y.lex : Y.lexInline)(t, i);
				i.hooks && (n = i.hooks.processAllTokens(n)), i.walkTokens && this.walkTokens(n, i.walkTokens);
				let r = (i.hooks ? i.hooks.provideParser(e) : e ? X.parse : X.parseInline)(n, i);
				return i.hooks && (r = i.hooks.postprocess(r)), r;
			} catch (e) {
				return a(e);
			}
		};
	}
	onError(e, t) {
		return (n) => {
			if (n.message += "\nPlease report this to https://github.com/markedjs/marked.", e) {
				let e = "<p>An error occurred:</p><pre>" + J(n.message + "", !0) + "</pre>";
				return t ? Promise.resolve(e) : e;
			}
			if (t) return Promise.reject(n);
			throw n;
		};
	}
}, li = new ci();
function Z(e, t) {
	return li.parse(e, t);
}
Z.options = Z.setOptions = function(e) {
	return li.setOptions(e), Z.defaults = li.defaults, En(Z.defaults), Z;
}, Z.getDefaults = Tn, Z.defaults = U;
function ui(...e) {
	return li.use(...e), Z.defaults = li.defaults, En(Z.defaults), Z;
}
Z.use = ui, Z.walkTokens = function(e, t) {
	return li.walkTokens(e, t);
}, Z.parseInline = li.parseInline, Z.Parser = X, Z.parser = X.parse, Z.Renderer = ii, Z.TextRenderer = ai, Z.Lexer = Y, Z.lexer = Y.lex, Z.Tokenizer = ri, Z.Hooks = oi, Z.parse = Z, Z.options, Z.setOptions, Z.walkTokens, Z.parseInline, X.parse, Y.lex;
//#endregion
//#region src/markdown.ts
var di = new ci({
	gfm: !0,
	breaks: !0,
	async: !1
});
wn.addHook("afterSanitizeAttributes", (e) => {
	e.tagName === "A" && (e.setAttribute("target", "_blank"), e.setAttribute("rel", "noopener noreferrer"));
});
var fi = /* @__PURE__ */ new Map();
function pi(e, t = !0) {
	if (t) {
		let t = fi.get(e);
		if (t !== void 0) return t;
	}
	let n = wn.sanitize(di.parse(e), {
		FORBID_TAGS: [
			"style",
			"form",
			"input",
			"button",
			"iframe",
			"img"
		],
		FORBID_ATTR: ["style"]
	});
	return t && (fi.size > 300 && fi.clear(), fi.set(e, n)), n;
}
//#endregion
//#region src/styles.ts
var mi = o`
  :host {
    display: block;
    height: 100vh;
    height: 100dvh;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, system-ui, sans-serif);
    --radius: 12px;
    --line: var(--divider-color, rgba(127, 127, 127, 0.25));
    --card: var(--card-background-color, #fff);
    --accent: var(--primary-color, #03a9f4);
    --muted: var(--secondary-text-color, #777);
    --danger: var(--error-color, #db4437);
    --ok: var(--success-color, #43a047);
    --warn: var(--warning-color, #ffa600);
  }
  .layout {
    display: flex;
    height: 100%;
    position: relative;
  }
  nav {
    width: 260px;
    flex: none;
    border-right: 1px solid var(--line);
    display: flex;
    flex-direction: column;
    padding: 12px;
    gap: 8px;
    box-sizing: border-box;
    background: var(--sidebar-background-color, var(--card));
  }
  .narrow nav {
    position: absolute;
    z-index: 3;
    top: 57px;
    bottom: 0;
    left: 0;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  }
  .convs {
    overflow-y: auto;
    flex: 1;
  }
  .conv {
    display: flex;
    align-items: center;
    padding: 8px 10px;
    border-radius: 8px;
    cursor: pointer;
    gap: 4px;
  }
  .conv:hover,
  .conv.active {
    background: rgba(127, 127, 127, 0.12);
  }
  .conv-title {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 14px;
  }
  .conv .icon {
    visibility: hidden;
  }
  .conv:hover .icon {
    visibility: visible;
  }
  main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  header {
    height: 56px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 12px;
    border-bottom: 1px solid var(--line);
    flex: none;
  }
  .title {
    flex: 1;
    font-size: 18px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px max(16px, calc((100% - 820px) / 2));
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .msg {
    line-height: 1.5;
    overflow-wrap: anywhere;
  }
  .msg.user {
    align-self: flex-end;
    background: var(--accent);
    color: var(--text-primary-color, #fff);
    padding: 8px 14px;
    border-radius: var(--radius) var(--radius) 4px var(--radius);
    max-width: 80%;
    white-space: pre-wrap;
  }
  .md :first-child {
    margin-top: 0;
  }
  .md :last-child {
    margin-bottom: 0;
  }
  .md pre,
  pre {
    background: rgba(127, 127, 127, 0.1);
    padding: 8px 10px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 12.5px;
    margin: 6px 0;
    white-space: pre;
  }
  .msg-actions {
    align-self: flex-end;
    display: flex;
    gap: 4px;
    margin-top: -4px;
  }
  .editing {
    color: var(--accent);
  }
  .md pre {
    position: relative;
  }
  .md pre .copy {
    position: absolute;
    top: 4px;
    right: 4px;
    opacity: 0;
    background: var(--card);
  }
  .md pre:hover .copy,
  .md pre .copy:focus-visible {
    opacity: 1;
  }
  @media (hover: none) {
    .md pre .copy {
      opacity: 1;
    }
  }
  .md code {
    font-size: 0.92em;
  }
  .md table {
    border-collapse: collapse;
  }
  .md td,
  .md th {
    border: 1px solid var(--line);
    padding: 4px 8px;
  }
  .md a {
    color: var(--accent);
  }
  .typing span {
    display: inline-block;
    width: 6px;
    height: 6px;
    margin-right: 4px;
    border-radius: 50%;
    background: var(--muted);
    animation: blink 1.2s infinite;
  }
  .typing span:nth-child(2) {
    animation-delay: 0.2s;
  }
  .typing span:nth-child(3) {
    animation-delay: 0.4s;
  }
  @keyframes blink {
    50% {
      opacity: 0.2;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .typing span {
      animation: none;
    }
  }
  .tool {
    border: 1px solid var(--line);
    border-radius: 10px;
    background: var(--card);
    font-size: 13.5px;
    position: relative;
  }
  .tool.waiting {
    border-color: var(--accent);
  }
  .tool.waiting.risky {
    border-color: var(--warn);
  }
  .tool summary {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    cursor: pointer;
    list-style: none;
  }
  .tool summary::-webkit-details-marker {
    display: none;
  }
  .tool details > :not(summary) {
    margin: 0 10px 8px;
  }
  .badge {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    flex: none;
    background: rgba(127, 127, 127, 0.18);
  }
  .ok .badge {
    background: var(--ok);
    color: #fff;
  }
  .error .badge {
    background: var(--danger);
    color: #fff;
  }
  .tool-name {
    font-weight: 500;
    flex: none;
  }
  .tool-summary {
    color: var(--muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }
  .tag {
    font-size: 11px;
    color: var(--muted);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0 6px;
  }
  .diff span {
    display: block;
  }
  .diff .add {
    color: var(--ok);
  }
  .diff .del {
    color: var(--danger);
  }
  .diff .hunk {
    color: var(--muted);
  }
  pre.result,
  pre.args {
    max-height: 240px;
    overflow: auto;
    white-space: pre-wrap;
  }
  .approval {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    padding: 0 10px 10px;
  }
  .approval .reason {
    width: 100%;
    font-size: 13px;
  }
  .approval input {
    flex: 1;
    min-width: 140px;
  }
  .undo {
    position: absolute;
    right: 8px;
    top: 6px;
  }
  .notice {
    font-size: 13px;
    color: var(--muted);
    text-align: center;
  }
  .notice.error {
    color: var(--danger);
  }
  .notice button {
    margin-left: 8px;
  }
  .welcome {
    margin: auto 0;
    text-align: center;
    color: var(--muted);
  }
  .welcome h2 {
    color: var(--primary-text-color);
    font-weight: 500;
  }
  .tips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-top: 16px;
  }
  .tip {
    border: 1px solid var(--line);
    background: var(--card);
    color: var(--primary-text-color);
    border-radius: 18px;
    padding: 8px 14px;
    cursor: pointer;
    font: inherit;
    font-size: 13.5px;
  }
  footer {
    padding: 8px max(16px, calc((100% - 820px) / 2)) 12px;
    flex: none;
  }
  .composer {
    display: flex;
    gap: 8px;
    align-items: flex-end;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 8px;
    background: var(--card);
  }
  textarea {
    flex: 1;
    border: none;
    resize: none;
    background: transparent;
    color: inherit;
    font: inherit;
    font-size: 15px;
    outline: none;
    max-height: 240px;
    padding: 6px;
  }
  .meta {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-top: 6px;
    font-size: 12.5px;
    color: var(--muted);
    flex-wrap: wrap;
  }
  .usage {
    margin-left: auto;
    white-space: nowrap;
  }
  select,
  input {
    background: var(--card);
    color: inherit;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 4px 6px;
    font: inherit;
  }
  input.model {
    width: 200px;
  }
  button {
    font: inherit;
    cursor: pointer;
    border-radius: 8px;
    border: 1px solid transparent;
    padding: 6px 14px;
  }
  button.primary {
    background: var(--accent);
    color: var(--text-primary-color, #fff);
  }
  button.danger {
    background: var(--danger);
    color: #fff;
  }
  button.ghost {
    background: transparent;
    color: var(--primary-text-color);
    border-color: var(--line);
  }
  button.icon {
    background: transparent;
    color: var(--muted);
    padding: 4px 8px;
  }
  button.small {
    padding: 2px 8px;
    font-size: 12px;
  }
  button.wide {
    width: 100%;
  }
  button:focus-visible,
  .tip:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .empty {
    padding: 32px;
    color: var(--muted);
  }
`;
//#endregion
//#region \0@oxc-project+runtime@0.154.0/helpers/esm/decorate.js
function Q(e, t, n, r) {
	var i = arguments.length, a = i < 3 ? t : r === null ? r = Object.getOwnPropertyDescriptor(t, n) : r, o;
	if (typeof Reflect == "object" && typeof Reflect.decorate == "function") a = Reflect.decorate(e, t, n, r);
	else for (var s = e.length - 1; s >= 0; s--) (o = e[s]) && (a = (i < 3 ? o(a) : i > 3 ? o(t, n, a) : o(t, n)) || a);
	return i > 3 && a && Object.defineProperty(t, n, a), a;
}
//#endregion
//#region src/panel.ts
var hi = {
	input: 0,
	output: 0,
	cache_read: 0,
	cache_write: 0,
	cost: 0
}, $ = class extends k {
	constructor(...e) {
		super(...e), this.narrow = !1, this.convs = [], this.convId = null, this.chatTitle = "New chat", this.items = [], this.usage = hi, this.running = !1, this.editing = !1, this.providerId = "", this.model = "", this.fetched = {}, this.showList = !1, this.loadError = "", this.started = !1, this.stickToBottom = !0, this.modelError = "", this.loadingModels = /* @__PURE__ */ new Set();
	}
	static {
		this.styles = mi;
	}
	get ws() {
		return this.hass.connection;
	}
	updated(e) {
		e.has("hass") && this.hass && !this.started && (this.started = !0, this.init()), this.stickToBottom && this.scroller && (this.scroller.scrollTop = this.scroller.scrollHeight), this.addCopyButtons();
	}
	addCopyButtons() {
		if (this.scroller) for (let e of this.scroller.querySelectorAll(".md pre:not([data-copy])")) {
			e.dataset.copy = "1";
			let t = document.createElement("button");
			t.className = "copy small ghost", t.textContent = "Copy", t.addEventListener("click", async () => {
				let n = e.querySelector("code") ?? e;
				try {
					await navigator.clipboard.writeText(n.textContent ?? ""), t.textContent = "Copied";
				} catch {
					t.textContent = "Copy failed";
				}
				setTimeout(() => t.textContent = "Copy", 1500);
			}), e.prepend(t);
		}
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this.detach(), this.started = !1;
	}
	async init() {
		try {
			this.info = await this.ws.sendMessagePromise({ type: "llm_agent/info" });
		} catch (e) {
			this.loadError = e.message ?? String(e);
			return;
		}
		let e = this.info.providers[0];
		e && !this.providerId && (this.providerId = e.id, this.model = e.default_model), await this.refreshList(), this.convId && await this.open(this.convId);
	}
	async refreshList() {
		this.convs = await this.ws.sendMessagePromise({ type: "llm_agent/conversations/list" });
	}
	get provider() {
		return this.info?.providers.find((e) => e.id === this.providerId);
	}
	async detach() {
		let e = this.unsub;
		if (this.unsub = void 0, e) try {
			await e();
		} catch {}
	}
	newChat() {
		this.editing = !1, this.detach(), this.convId = null, this.chatTitle = "New chat", this.items = [], this.usage = hi, this.running = !1, this.showList = !1;
		let e = this.provider ?? this.info?.providers[0];
		e && (this.model = e.default_model), this.input?.focus();
	}
	async open(e) {
		await this.detach(), this.showList = !1, this.editing = !1;
		let t = await this.ws.sendMessagePromise({
			type: "llm_agent/conversations/get",
			conversation_id: e
		});
		this.convId = t.id, this.chatTitle = t.title, this.usage = t.usage, this.providerId = t.provider_id, this.model = t.model, this.items = _i(t.messages), t.stopped && t.stopped_text && this.items.push({
			kind: "notice",
			text: t.stopped_text,
			stop: t.stopped
		}), this.running = !1, this.stickToBottom = !0, (await this.ws.sendMessagePromise({ type: "llm_agent/info" })).running.includes(e) && (this.running = !0, this.items = [...this.items, {
			kind: "assistant",
			text: ""
		}], this.unsub = await this.ws.subscribeMessage((e) => this.onEvent(e), {
			type: "llm_agent/attach",
			conversation_id: e
		}));
	}
	async removeConv(e, t) {
		t.stopPropagation(), confirm("Delete this conversation?") && (await this.ws.sendMessagePromise({
			type: "llm_agent/conversations/delete",
			conversation_id: e
		}), e === this.convId && this.newChat(), await this.refreshList());
	}
	lastUserIndex() {
		for (let e = this.items.length - 1; e >= 0; e--) if (this.items[e].kind === "user") return e;
		return -1;
	}
	async send(e) {
		let t = e !== void 0 || this.editing, n = e ?? this.input?.value.trim();
		if (!n || this.running) return;
		e === void 0 && (this.input.value = "", this.autosize()), this.editing = !1;
		let r = this.lastUserIndex(), i = t && r >= 0 ? this.items.slice(0, r) : this.items;
		this.items = [
			...i,
			{
				kind: "user",
				text: n
			},
			{
				kind: "assistant",
				text: ""
			}
		], this.running = !0, this.stickToBottom = !0;
		try {
			let e = !0;
			this.unsub = await this.ws.subscribeMessage((t) => {
				e && "conversation_id" in t || (e = !1, this.onEvent(t));
			}, {
				type: "llm_agent/chat",
				text: n,
				conversation_id: this.convId,
				provider_id: this.providerId || void 0,
				model: this.model || void 0,
				rewind: t || void 0
			});
		} catch (e) {
			this.running = !1, this.push({
				kind: "notice",
				text: Ci(e),
				error: !0
			});
			return;
		}
		this.convId || (await this.refreshList(), this.convId = this.convs[0]?.id ?? null, this.chatTitle = this.convs[0]?.title ?? n.slice(0, 60));
	}
	onEvent(e) {
		switch (e.type) {
			case "delta": {
				let t = this.items[this.items.length - 1];
				t?.kind === "assistant" ? t.text += e.text : this.items.push({
					kind: "assistant",
					text: e.text
				}), this.scheduleRender();
				return;
			}
			case "tool_start":
				this.push({
					kind: "tool",
					id: e.call_id,
					name: e.name,
					args: e.args,
					status: "running"
				});
				return;
			case "approval":
				this.patchTool(e.call_id, {
					status: "waiting",
					approval: {
						summary: e.summary,
						reason: e.reason,
						risky: e.risky,
						diff: e.diff
					}
				}, {
					kind: "tool",
					id: e.call_id,
					name: e.name,
					args: e.args,
					status: "waiting"
				});
				return;
			case "tool_result":
				this.patchTool(e.call_id, {
					status: e.ok ? "ok" : "error",
					summary: e.summary,
					preview: e.preview,
					snapshotId: e.snapshot_id,
					approval: void 0
				}), this.push({
					kind: "assistant",
					text: ""
				});
				return;
			case "usage":
				this.usage = e.usage;
				return;
			case "notice":
				this.push({
					kind: "notice",
					text: e.text,
					stop: e.stop
				});
				return;
			case "error":
				this.push({
					kind: "notice",
					text: e.message,
					error: !0
				});
				return;
			case "done":
				this.usage = e.usage, this.running = !1, this.items = this.items.filter((e) => !(e.kind === "assistant" && !e.text)), this.detach(), this.refreshList().then(() => {
					this.chatTitle = this.convs.find((e) => e.id === this.convId)?.title ?? this.chatTitle;
				});
				return;
		}
	}
	scheduleRender() {
		this.renderTimer === void 0 && (this.renderTimer = window.setTimeout(() => {
			this.renderTimer = void 0, this.requestUpdate();
		}, 80));
	}
	push(e) {
		let t = this.items.filter((e) => !(e.kind === "assistant" && !e.text));
		this.items = [...t, e];
	}
	patchTool(e, t, n) {
		let r = !1;
		this.items = this.items.map((n) => n.kind === "tool" && n.id === e ? (r = !0, {
			...n,
			...t
		}) : n), !r && n && this.push({
			...n,
			...t
		});
	}
	async answer(e, t) {
		let n = this.renderRoot.querySelector(`#note-${CSS.escape(e)}`)?.value ?? "";
		this.patchTool(e, {
			status: "running",
			approval: void 0
		});
		try {
			await this.ws.sendMessagePromise({
				type: "llm_agent/approve",
				conversation_id: this.convId,
				call_id: e,
				approved: t,
				note: n
			});
		} catch (e) {
			this.push({
				kind: "notice",
				text: Ci(e),
				error: !0
			});
		}
	}
	async undo(e) {
		if (e.snapshotId && confirm(`Undo "${e.summary || e.name}"?`)) try {
			let t = await this.ws.sendMessagePromise({
				type: "llm_agent/undo",
				snapshot_id: e.snapshotId,
				...this.convId ? { conversation_id: this.convId } : {}
			});
			this.patchTool(e.id, { undone: !0 }), this.push({
				kind: "notice",
				text: `Undone: ${t.summary}`
			});
		} catch (e) {
			this.push({
				kind: "notice",
				text: Ci(e),
				error: !0
			});
		}
	}
	async stop() {
		this.convId && await this.ws.sendMessagePromise({
			type: "llm_agent/cancel",
			conversation_id: this.convId
		});
	}
	async loadModels() {
		let e = this.providerId;
		if (!(!e || e in this.fetched || this.loadingModels.has(e))) {
			this.loadingModels.add(e);
			try {
				let t = await this.ws.sendMessagePromise({
					type: "llm_agent/models",
					provider_id: e
				});
				this.modelError = t.error ?? "", this.fetched = {
					...this.fetched,
					[e]: t.models
				};
			} catch {} finally {
				this.loadingModels.delete(e);
			}
		}
	}
	continueTurn() {
		this.input.value = "Continue.", this.send();
	}
	editLast(e) {
		this.editing = !0, this.input.value = e, this.autosize(), this.input.focus();
	}
	cancelEdit() {
		this.editing = !1, this.input.value = "", this.autosize();
	}
	onKey(e) {
		e.key === "Enter" && !e.shiftKey && !e.isComposing && (e.preventDefault(), this.send());
	}
	autosize() {
		let e = this.input;
		e && (e.style.height = "auto", e.style.height = `${Math.min(e.scrollHeight, 240)}px`);
	}
	onScroll() {
		let e = this.scroller;
		e && (this.stickToBottom = e.scrollHeight - e.scrollTop - e.clientHeight < 40);
	}
	pickProvider(e) {
		this.providerId = e.target.value, this.model = this.provider?.default_model ?? "";
	}
	render() {
		if (this.loadError) return S`<div class="empty">
        LLM Agent could not load: ${this.loadError}
      </div>`;
		if (this.info && !this.info.providers.length) return S`<div class="empty">
        No AI provider is configured. Add one under Settings → Devices &amp;
        services → LLM Agent → Configure.
      </div>`;
		let e = !this.narrow || this.showList, t = this.convId ? this.lastUserIndex() : -1;
		return S`
      <div class="layout ${this.narrow ? "narrow" : ""}">
        ${e ? this.renderList() : C}
        <main>
          <header>
            <ha-menu-button
              .hass=${this.hass}
              .narrow=${this.narrow}
            ></ha-menu-button>
            ${this.narrow ? S`<button
                    class="icon"
                    title="Conversations"
                    aria-label="Conversations"
                    @click=${() => this.showList = !this.showList}
                  >
                    <ha-icon icon="mdi:forum-outline"></ha-icon>
                  </button>` : C}
            <div class="title">${this.chatTitle}</div>
            <button class="ghost" @click=${this.newChat}>New chat</button>
          </header>
          <div class="messages" @scroll=${this.onScroll}>
            ${this.items.length ? C : this.renderWelcome()}
            ${nt(this.items, (e, t) => t, (e, n) => this.renderItem(e, n === this.items.length - 1, n === t))}
          </div>
          ${this.renderComposer()}
        </main>
      </div>
    `;
	}
	renderList() {
		return S`<nav>
      <button class="primary wide" @click=${this.newChat}>+ New chat</button>
      <div class="convs">
        ${this.convs.map((e) => S`<div
              class="conv ${e.id === this.convId ? "active" : ""}"
              @click=${() => this.open(e.id)}
            >
              <span class="conv-title">${e.title}</span>
              <button
                class="icon small"
                title="Delete"
                @click=${(t) => this.removeConv(e.id, t)}
              >
                ✕
              </button>
            </div>`)}
      </div>
    </nav>`;
	}
	renderWelcome() {
		return S`<div class="welcome">
      <h2>What should I do?</h2>
      <p>
        I can control devices, answer questions about your home, and build
        automations, scenes, scripts and dashboards. Mode:
        <b>${Si(this.info?.approval_mode)}</b>.
      </p>
      <div class="tips">
        ${[
			"Turn off all the lights downstairs",
			"Make a dashboard for the living room",
			"Create an automation: porch light on at sunset, off at 11pm",
			"Why did the hallway sensor go unavailable yesterday?"
		].map((e) => S`<button
              class="tip"
              @click=${() => {
			this.input.value = e, this.input.focus();
		}}
            >
              ${e}
            </button>`)}
      </div>
    </div>`;
	}
	renderItem(e, t, n = !1) {
		switch (e.kind) {
			case "user": return S`<div class="msg user">${e.text}</div>
          ${n && !this.running ? S`<div class="msg-actions">
                  <button
                    class="small ghost"
                    @click=${() => this.editLast(e.text)}
                  >
                    Edit
                  </button>
                  <button
                    class="small ghost"
                    @click=${() => this.send(e.text)}
                  >
                    Retry
                  </button>
                </div>` : C}`;
			case "assistant": return e.text ? S`<div class="msg assistant md">
          ${Ke(pi(e.text, !(t && this.running)))}
        </div>` : t && this.running ? S`<div class="msg assistant typing">
                <span></span><span></span><span></span>
              </div>` : C;
			case "notice": return S`<div class="notice ${e.error ? "error" : ""}">
          ${e.text}
          ${t && !this.running && e.stop && gi.has(e.stop) ? S`<button class="small" @click=${this.continueTurn}>
                Continue
              </button>` : C}
        </div>`;
			case "tool": return this.renderTool(e);
		}
	}
	renderTool(e) {
		let t = {
			running: "⋯",
			ok: "✓",
			error: "!",
			waiting: "?"
		}[e.status], n = e.approval;
		return S`<div
      class="tool ${e.status} ${n?.risky ? "risky" : ""}"
    >
      <details ?open=${!!n}>
        <summary>
          <span class="badge">${t}</span>
          <span class="tool-name">${yi(e.name)}</span>
          <span class="tool-summary"
            >${n?.summary ?? e.summary ?? bi(e.args)}</span
          >
          ${e.undone ? S`<span class="tag">undone</span>` : C}
        </summary>
        ${n?.diff ? S`<pre class="diff">${vi(n.diff)}</pre>` : C}
        ${n ? C : S`<pre class="args">${JSON.stringify(e.args, null, 2)}</pre>`}
        ${e.preview && !n ? S`<pre class="result">${e.preview}</pre>` : C}
      </details>
      ${n ? S`<div class="approval">
              <div class="reason">
                ${n.risky ? "⚠ " : ""}Needs your
                approval${n.reason ? `: ${n.reason}` : ""}
              </div>
              <input
                id="note-${e.id}"
                placeholder="Optional note for the AI"
              />
              <button
                class="danger"
                @click=${() => this.answer(e.id, !1)}
              >
                Deny
              </button>
              <button
                class="primary"
                @click=${() => this.answer(e.id, !0)}
              >
                Approve
              </button>
            </div>` : C}
      ${e.snapshotId && !e.undone && e.status === "ok" ? S`<button
              class="ghost small undo"
              @click=${() => this.undo(e)}
            >
              Undo
            </button>` : C}
    </div>`;
	}
	renderComposer() {
		let e = this.provider, t = "models";
		return S`<footer>
      <div class="composer">
        <textarea
          rows="1"
          placeholder="Ask or tell me to do something…"
          @keydown=${this.onKey}
          @input=${this.autosize}
        ></textarea>
        ${this.running ? S`<button class="danger" @click=${this.stop}>Stop</button>` : S`<button class="primary" @click=${() => this.send()}>
                Send
              </button>`}
      </div>
      <div class="meta">
        ${this.editing ? S`<span class="editing"
                >Editing your last message
                <button class="small ghost" @click=${this.cancelEdit}>
                  Cancel
                </button></span
              >` : C}
        <select
          @change=${this.pickProvider}
          .value=${this.providerId}
          ?disabled=${this.running}
        >
          ${this.info?.providers.map((e) => S`<option
                value=${e.id}
                ?selected=${e.id === this.providerId}
              >
                ${e.name}
              </option>`)}
        </select>
        <input
          class="model"
          list=${t}
          .value=${this.model}
          ?disabled=${this.running}
          @change=${(e) => this.model = e.target.value.trim()}
          @focus=${this.loadModels}
          title=${this.modelError || "Model id (pick or type)"}
        />
        <datalist id=${t}>
          ${(this.fetched[this.providerId] ?? e?.models)?.map((e) => S`<option value=${e.id}>${e.label}</option>`)}
        </datalist>
        <span
          class="usage"
          title="Tokens in / out (cached). Cost is an estimate."
        >
          ${xi(this.usage.input + this.usage.cache_read + this.usage.cache_write)}
          in · ${xi(this.usage.output)} out
          ${this.usage.cache_read ? S` · ${xi(this.usage.cache_read)} cached` : C}
          ·
          ${this.usage.cost == null ? "cost n/a" : `~$${this.usage.cost.toFixed(this.usage.cost < 1 ? 4 : 2)}`}
        </span>
      </div>
    </footer>`;
	}
};
Q([ze({ attribute: !1 })], $.prototype, "hass", void 0), Q([ze({ type: Boolean })], $.prototype, "narrow", void 0), Q([A()], $.prototype, "info", void 0), Q([A()], $.prototype, "convs", void 0), Q([A()], $.prototype, "convId", void 0), Q([A()], $.prototype, "chatTitle", void 0), Q([A()], $.prototype, "items", void 0), Q([A()], $.prototype, "usage", void 0), Q([A()], $.prototype, "running", void 0), Q([A()], $.prototype, "editing", void 0), Q([A()], $.prototype, "providerId", void 0), Q([A()], $.prototype, "model", void 0), Q([A()], $.prototype, "fetched", void 0), Q([A()], $.prototype, "showList", void 0), Q([A()], $.prototype, "loadError", void 0), Q([Ve("textarea")], $.prototype, "input", void 0), Q([Ve(".messages")], $.prototype, "scroller", void 0);
var gi = /* @__PURE__ */ new Set([
	"length",
	"tool_limit",
	"cancelled"
]);
function _i(e) {
	let t = [], n = /* @__PURE__ */ new Map();
	for (let r of e) if (r.role === "user") t.push({
		kind: "user",
		text: r.content
	});
	else if (r.role === "assistant") {
		r.content && t.push({
			kind: "assistant",
			text: r.content
		});
		for (let e of r.tool_calls) n.set(e.id, {
			name: e.name,
			args: e.args
		});
	} else {
		let e = n.get(r.tool_call_id);
		t.push({
			kind: "tool",
			id: r.tool_call_id,
			name: r.name,
			args: e?.args ?? {},
			status: r.ok ? "ok" : "error",
			summary: r.summary || (r.decision === "denied" ? "Denied" : ""),
			preview: r.preview,
			snapshotId: r.snapshot_id,
			undone: r.undone
		});
	}
	return t;
}
function vi(e) {
	return e.replace(/\n+$/, "").split("\n").map((e) => S`<span class=${e.startsWith("+") && !e.startsWith("+++") ? "add" : e.startsWith("-") && !e.startsWith("---") ? "del" : e.startsWith("@@") ? "hunk" : ""}>${e || " "}</span>`);
}
function yi(e) {
	return e.replace(/_/g, " ");
}
function bi(e) {
	let t = Object.entries(e).filter(([e]) => !e.startsWith("_")).map(([e, t]) => `${e}=${typeof t == "string" ? t : JSON.stringify(t)}`).join(" ");
	return t.length > 120 ? `${t.slice(0, 117)}…` : t;
}
function xi(e) {
	return e >= 1e6 ? `${(e / 1e6).toFixed(1)}M` : e >= 1e3 ? `${(e / 1e3).toFixed(1)}k` : String(e);
}
function Si(e) {
	return {
		ask_all: "ask before every change",
		ask_risky: "ask before risky actions",
		autopilot: "autopilot"
	}[e ?? ""] ?? "";
}
function Ci(e) {
	return e.message ?? String(e);
}
customElements.get("llm-agent-panel") || customElements.define("llm-agent-panel", $);
//#endregion
