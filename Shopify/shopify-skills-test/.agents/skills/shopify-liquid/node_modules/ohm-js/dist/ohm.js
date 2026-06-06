(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports) :
  typeof define === 'function' && define.amd ? define(['exports'], factory) :
  (global = typeof globalThis !== 'undefined' ? globalThis : global || self, factory(global.ohm = {}));
})(this, (function (exports) { 'use strict';

  // --------------------------------------------------------------------

  // --------------------------------------------------------------------
  // Exports
  // --------------------------------------------------------------------

  function abstract(optMethodName) {
    const methodName = optMethodName || '';
    return function () {
      throw new Error(
        'this method ' +
          methodName +
          ' is abstract! ' +
          '(it has no implementation in class ' +
          this.constructor.name +
          ')'
      );
    };
  }

  function assert(cond, message) {
    if (!cond) {
      throw new Error(message || 'Assertion failed');
    }
  }

  // Define a lazily-computed, non-enumerable property named `propName`
  // on the object `obj`. `getterFn` will be called to compute the value the
  // first time the property is accessed.
  function defineLazyProperty(obj, propName, getterFn) {
    let memo;
    Object.defineProperty(obj, propName, {
      get() {
        if (!memo) {
          memo = getterFn.call(this);
        }
        return memo;
      },
    });
  }

  function clone(obj) {
    if (obj) {
      return Object.assign({}, obj);
    }
    return obj;
  }

  function repeatFn(fn, n) {
    const arr = [];
    while (n-- > 0) {
      arr.push(fn());
    }
    return arr;
  }

  function repeatStr(str, n) {
    return new Array(n + 1).join(str);
  }

  function repeat(x, n) {
    return repeatFn(() => x, n);
  }

  function getDuplicates(array) {
    const duplicates = [];
    for (let idx = 0; idx < array.length; idx++) {
      const x = array[idx];
      if (array.lastIndexOf(x) !== idx && duplicates.indexOf(x) < 0) {
        duplicates.push(x);
      }
    }
    return duplicates;
  }

  function copyWithoutDuplicates(array) {
    const noDuplicates = [];
    array.forEach(entry => {
      if (noDuplicates.indexOf(entry) < 0) {
        noDuplicates.push(entry);
      }
    });
    return noDuplicates;
  }

  function isSyntactic(ruleName) {
    const firstChar = ruleName[0];
    return firstChar === firstChar.toUpperCase();
  }

  function isLexical(ruleName) {
    return !isSyntactic(ruleName);
  }

  function padLeft(str, len, optChar) {
    const ch = optChar || ' ';
    if (str.length < len) {
      return repeatStr(ch, len - str.length) + str;
    }
    return str;
  }

  // StringBuffer

  function StringBuffer() {
    this.strings = [];
  }

  StringBuffer.prototype.append = function (str) {
    this.strings.push(str);
  };

  StringBuffer.prototype.contents = function () {
    return this.strings.join('');
  };

  const escapeUnicode = str => String.fromCodePoint(parseInt(str, 16));

  function unescapeCodePoint(s) {
    if (s.charAt(0) === '\\') {
      switch (s.charAt(1)) {
        case 'b':
          return '\b';
        case 'f':
          return '\f';
        case 'n':
          return '\n';
        case 'r':
          return '\r';
        case 't':
          return '\t';
        case 'v':
          return '\v';
        case 'x':
          return escapeUnicode(s.slice(2, 4));
        case 'u':
          return s.charAt(2) === '{'
            ? escapeUnicode(s.slice(3, -1))
            : escapeUnicode(s.slice(2, 6));
        default:
          return s.charAt(1);
      }
    } else {
      return s;
    }
  }

  // Helper for producing a description of an unknown object in a safe way.
  // Especially useful for error messages where an unexpected type of object was encountered.
  function unexpectedObjToString(obj) {
    if (obj == null) {
      return String(obj);
    }
    const baseToString = Object.prototype.toString.call(obj);
    try {
      let typeName;
      if (obj.constructor && obj.constructor.name) {
        typeName = obj.constructor.name;
      } else if (baseToString.indexOf('[object ') === 0) {
        typeName = baseToString.slice(8, -1); // Extract e.g. "Array" from "[object Array]".
      } else {
        typeName = typeof obj;
      }
      return typeName + ': ' + JSON.stringify(String(obj));
    } catch {
      return baseToString;
    }
  }

  function checkNotNull(obj, message = 'unexpected null value') {
    if (obj == null) {
      throw new Error(message);
    }
    return obj;
  }

  var common = /*#__PURE__*/Object.freeze({
    __proto__: null,
    abstract: abstract,
    assert: assert,
    defineLazyProperty: defineLazyProperty,
    clone: clone,
    repeatFn: repeatFn,
    repeatStr: repeatStr,
    repeat: repeat,
    getDuplicates: getDuplicates,
    copyWithoutDuplicates: copyWithoutDuplicates,
    isSyntactic: isSyntactic,
    isLexical: isLexical,
    padLeft: padLeft,
    StringBuffer: StringBuffer,
    unescapeCodePoint: unescapeCodePoint,
    unexpectedObjToString: unexpectedObjToString,
    checkNotNull: checkNotNull
  });

  // The full list of categories from:
  // https://www.unicode.org/Public/UCD/latest/ucd/extracted/DerivedGeneralCategory.txt.

  const toRegExp = val => new RegExp(String.raw`\p{${val}}`, 'u');

  /*
    grep -v '^#' DerivedGeneralCategory.txt \
      | cut -d';' -f2 \
      | awk 'NF{print $1}' \
      | sort -u \
      | awk '{printf "\x27%s\x27,\n",$1}'
   */

  const UnicodeCategories = Object.fromEntries(
    [
      'Cc',
      'Cf',
      'Cn',
      'Co',
      'Cs',
      'Ll',
      'Lm',
      'Lo',
      'Lt',
      'Lu',
      'Mc',
      'Me',
      'Mn',
      'Nd',
      'Nl',
      'No',
      'Pc',
      'Pd',
      'Pe',
      'Pf',
      'Pi',
      'Po',
      'Ps',
      'Sc',
      'Sk',
      'Sm',
      'So',
      'Zl',
      'Zp',
      'Zs',
    ].map(cat => [cat, toRegExp(cat)])
  );
  UnicodeCategories['Ltmo'] = /\p{Lt}|\p{Lm}|\p{Lo}/u;

  // We only support a few of these for now, but could add more later.
  // See https://www.unicode.org/Public/UCD/latest/ucd/PropertyAliases.txt
  const UnicodeBinaryProperties = Object.fromEntries(
    ['XID_Start', 'XID_Continue', 'White_Space'].map(prop => [prop, toRegExp(prop)])
  );

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  // General stuff

  class PExpr {
    constructor() {
      if (this.constructor === PExpr) {
        throw new Error("PExpr cannot be instantiated -- it's abstract");
      }
    }

    // Set the `source` property to the interval containing the source for this expression.
    withSource(interval) {
      if (interval) {
        this.source = interval.trimmed();
      }
      return this;
    }
  }

  // Any

  const any = Object.create(PExpr.prototype);

  // End

  const end = Object.create(PExpr.prototype);

  // Terminals

  class Terminal extends PExpr {
    constructor(obj) {
      super();
      this.obj = obj;
    }
  }

  // Ranges

  class Range extends PExpr {
    constructor(from, to) {
      super();
      this.from = from;
      this.to = to;
      // If either `from` or `to` is made up of multiple code units, then
      // the range should consume a full code point, not a single code unit.
      this.matchCodePoint = from.length > 1 || to.length > 1;
    }
  }

  // Parameters

  class Param extends PExpr {
    constructor(index) {
      super();
      this.index = index;
    }
  }

  // Alternation

  class Alt extends PExpr {
    constructor(terms) {
      super();
      this.terms = terms;
    }
  }

  // Extend is an implementation detail of rule extension

  class Extend extends Alt {
    constructor(superGrammar, name, body) {
      const origBody = superGrammar.rules[name].body;
      super([body, origBody]);

      this.superGrammar = superGrammar;
      this.name = name;
      this.body = body;
    }
  }

  // Splice is an implementation detail of rule overriding with the `...` operator.
  class Splice extends Alt {
    constructor(superGrammar, ruleName, beforeTerms, afterTerms) {
      const origBody = superGrammar.rules[ruleName].body;
      super([...beforeTerms, origBody, ...afterTerms]);

      this.superGrammar = superGrammar;
      this.ruleName = ruleName;
      this.expansionPos = beforeTerms.length;
    }
  }

  // Sequences

  class Seq extends PExpr {
    constructor(factors) {
      super();
      this.factors = factors;
    }
  }

  // Iterators and optionals

  class Iter extends PExpr {
    constructor(expr) {
      super();
      this.expr = expr;
    }
  }

  class Star extends Iter {}
  class Plus extends Iter {}
  class Opt extends Iter {}

  Star.prototype.operator = '*';
  Plus.prototype.operator = '+';
  Opt.prototype.operator = '?';

  Star.prototype.minNumMatches = 0;
  Plus.prototype.minNumMatches = 1;
  Opt.prototype.minNumMatches = 0;

  Star.prototype.maxNumMatches = Number.POSITIVE_INFINITY;
  Plus.prototype.maxNumMatches = Number.POSITIVE_INFINITY;
  Opt.prototype.maxNumMatches = 1;

  // Predicates

  class Not extends PExpr {
    constructor(expr) {
      super();
      this.expr = expr;
    }
  }

  class Lookahead extends PExpr {
    constructor(expr) {
      super();
      this.expr = expr;
    }
  }

  // "Lexification"

  class Lex extends PExpr {
    constructor(expr) {
      super();
      this.expr = expr;
    }
  }

  // Rule application

  class Apply extends PExpr {
    constructor(ruleName, args = []) {
      super();
      this.ruleName = ruleName;
      this.args = args;
    }

    isSyntactic() {
      return isSyntactic(this.ruleName);
    }

    // This method just caches the result of `this.toString()` in a non-enumerable property.
    toMemoKey() {
      if (!this._memoKey) {
        Object.defineProperty(this, '_memoKey', {value: this.toString()});
      }
      return this._memoKey;
    }
  }

  // Unicode character

  class UnicodeChar extends PExpr {
    constructor(categoryOrProp) {
      super();
      this.categoryOrProp = categoryOrProp;
      if (categoryOrProp in UnicodeCategories) {
        this.pattern = UnicodeCategories[categoryOrProp];
      } else if (categoryOrProp in UnicodeBinaryProperties) {
        this.pattern = UnicodeBinaryProperties[categoryOrProp];
      } else {
        throw new Error(
          `Invalid Unicode category or property name: ${JSON.stringify(categoryOrProp)}`
        );
      }
    }
  }

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  function createError(message, optInterval) {
    let e;
    if (optInterval) {
      e = new Error(optInterval.getLineAndColumnMessage() + message);
      e.shortMessage = message;
      e.interval = optInterval;
    } else {
      e = new Error(message);
    }
    return e;
  }

  // ----------------- errors about intervals -----------------

  function intervalSourcesDontMatch() {
    return createError("Interval sources don't match");
  }

  // ----------------- errors about grammars -----------------

  // Grammar syntax error

  function grammarSyntaxError(matchFailure) {
    const e = new Error();
    Object.defineProperty(e, 'message', {
      enumerable: true,
      get() {
        return matchFailure.message;
      },
    });
    Object.defineProperty(e, 'shortMessage', {
      enumerable: true,
      get() {
        return 'Expected ' + matchFailure.getExpectedText();
      },
    });
    e.interval = matchFailure.getInterval();
    return e;
  }

  // Undeclared grammar

  function undeclaredGrammar(grammarName, namespace, interval) {
    const message = namespace
      ? `Grammar ${grammarName} is not declared in namespace '${namespace}'`
      : 'Undeclared grammar ' + grammarName;
    return createError(message, interval);
  }

  // Duplicate grammar declaration

  function duplicateGrammarDeclaration(grammar, namespace) {
    return createError('Grammar ' + grammar.name + ' is already declared in this namespace');
  }

  function grammarDoesNotSupportIncrementalParsing(grammar) {
    return createError(`Grammar '${grammar.name}' does not support incremental parsing`);
  }

  // ----------------- rules -----------------

  // Undeclared rule

  function undeclaredRule(ruleName, grammarName, optInterval) {
    return createError(
      'Rule ' + ruleName + ' is not declared in grammar ' + grammarName,
      optInterval
    );
  }

  // Cannot override undeclared rule

  function cannotOverrideUndeclaredRule(ruleName, grammarName, optSource) {
    return createError(
      'Cannot override rule ' + ruleName + ' because it is not declared in ' + grammarName,
      optSource
    );
  }

  // Cannot extend undeclared rule

  function cannotExtendUndeclaredRule(ruleName, grammarName, optSource) {
    return createError(
      'Cannot extend rule ' + ruleName + ' because it is not declared in ' + grammarName,
      optSource
    );
  }

  // Duplicate rule declaration

  function duplicateRuleDeclaration(ruleName, grammarName, declGrammarName, optSource) {
    let message =
      "Duplicate declaration for rule '" + ruleName + "' in grammar '" + grammarName + "'";
    if (grammarName !== declGrammarName) {
      message += " (originally declared in '" + declGrammarName + "')";
    }
    return createError(message, optSource);
  }

  // Wrong number of parameters

  function wrongNumberOfParameters(ruleName, expected, actual, source) {
    return createError(
      'Wrong number of parameters for rule ' +
        ruleName +
        ' (expected ' +
        expected +
        ', got ' +
        actual +
        ')',
      source
    );
  }

  // Wrong number of arguments

  function wrongNumberOfArguments(ruleName, expected, actual, expr) {
    return createError(
      'Wrong number of arguments for rule ' +
        ruleName +
        ' (expected ' +
        expected +
        ', got ' +
        actual +
        ')',
      expr
    );
  }

  // Duplicate parameter names

  function duplicateParameterNames(ruleName, duplicates, source) {
    return createError(
      'Duplicate parameter names in rule ' + ruleName + ': ' + duplicates.join(', '),
      source
    );
  }

  // Invalid parameter expression

  function invalidParameter(ruleName, expr) {
    return createError(
      'Invalid parameter to rule ' +
        ruleName +
        ': ' +
        expr +
        ' has arity ' +
        expr.getArity() +
        ', but parameter expressions must have arity 1',
      expr.source
    );
  }

  // Application of syntactic rule from lexical rule

  const syntacticVsLexicalNote =
    'NOTE: A _syntactic rule_ is a rule whose name begins with a capital letter. ' +
    'See https://ohmjs.org/d/svl for more details.';

  function applicationOfSyntacticRuleFromLexicalContext(ruleName, applyExpr) {
    return createError(
      'Cannot apply syntactic rule ' + ruleName + ' from here (inside a lexical context)',
      applyExpr.source
    );
  }

  // Lexical rule application used with applySyntactic

  function applySyntacticWithLexicalRuleApplication(applyExpr) {
    const {ruleName} = applyExpr;
    return createError(
      `applySyntactic is for syntactic rules, but '${ruleName}' is a lexical rule. ` +
        syntacticVsLexicalNote,
      applyExpr.source
    );
  }

  // Application of applySyntactic in a syntactic context

  function unnecessaryExperimentalApplySyntactic(applyExpr) {
    return createError(
      'applySyntactic is not required here (in a syntactic context)',
      applyExpr.source
    );
  }

  // Incorrect argument type

  function incorrectArgumentType(expectedType, expr) {
    return createError('Incorrect argument type: expected ' + expectedType, expr.source);
  }

  // Multiple instances of the super-splice operator (`...`) in the rule body.

  function multipleSuperSplices(expr) {
    return createError("'...' can appear at most once in a rule body", expr.source);
  }

  // Unicode code point escapes

  function invalidCodePoint(applyWrapper) {
    const node = applyWrapper._node;
    assert(node && node.isNonterminal() && node.ctorName === 'escapeChar_unicodeCodePoint');

    // Get an interval that covers all of the hex digits.
    const digitIntervals = applyWrapper.children.slice(1, -1).map(d => d.source);
    const fullInterval = digitIntervals[0].coverageWith(...digitIntervals.slice(1));
    return createError(
      `U+${fullInterval.contents} is not a valid Unicode code point`,
      fullInterval
    );
  }

  // ----------------- Kleene operators -----------------

  function kleeneExprHasNullableOperand(kleeneExpr, applicationStack) {
    const actuals =
      applicationStack.length > 0 ? applicationStack[applicationStack.length - 1].args : [];
    const expr = kleeneExpr.expr.substituteParams(actuals);
    let message =
      'Nullable expression ' +
      expr +
      " is not allowed inside '" +
      kleeneExpr.operator +
      "' (possible infinite loop)";
    if (applicationStack.length > 0) {
      const stackTrace = applicationStack
        .map(app => new Apply(app.ruleName, app.args))
        .join('\n');
      message += '\nApplication stack (most recent application last):\n' + stackTrace;
    }
    return createError(message, kleeneExpr.expr.source);
  }

  // ----------------- arity -----------------

  function inconsistentArity(ruleName, expected, actual, expr) {
    return createError(
      'Rule ' +
        ruleName +
        ' involves an alternation which has inconsistent arity ' +
        '(expected ' +
        expected +
        ', got ' +
        actual +
        ')',
      expr.source
    );
  }

  // ----------------- convenience -----------------

  function multipleErrors(errors) {
    const messages = errors.map(e => e.message);
    return createError(['Errors:'].concat(messages).join('\n- '), errors[0].interval);
  }

  // ----------------- semantic -----------------

  function missingSemanticAction(ctorName, name, type, stack) {
    let stackTrace = stack
      .slice(0, -1)
      .map(info => {
        const ans = '  ' + info[0].name + ' > ' + info[1];
        return info.length === 3 ? ans + " for '" + info[2] + "'" : ans;
      })
      .join('\n');
    stackTrace += '\n  ' + name + ' > ' + ctorName;

    let moreInfo = '';
    if (ctorName === '_iter') {
      moreInfo = [
        '\nNOTE: as of Ohm v16, there is no default action for iteration nodes — see ',
        '  https://ohmjs.org/d/dsa for details.',
      ].join('\n');
    }

    const message = [
      `Missing semantic action for '${ctorName}' in ${type} '${name}'.${moreInfo}`,
      'Action stack (most recent call last):',
      stackTrace,
    ].join('\n');

    const e = createError(message);
    e.name = 'missingSemanticAction';
    return e;
  }

  function throwErrors(errors) {
    if (errors.length === 1) {
      throw errors[0];
    }
    if (errors.length > 1) {
      throw multipleErrors(errors);
    }
  }

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  // Given an array of numbers `arr`, return an array of the numbers as strings,
  // right-justified and padded to the same length.
  function padNumbersToEqualLength(arr) {
    let maxLen = 0;
    const strings = arr.map(n => {
      const str = n.toString();
      maxLen = Math.max(maxLen, str.length);
      return str;
    });
    return strings.map(s => padLeft(s, maxLen));
  }

  // Produce a new string that would be the result of copying the contents
  // of the string `src` onto `dest` at offset `offest`.
  function strcpy(dest, src, offset) {
    const origDestLen = dest.length;
    const start = dest.slice(0, offset);
    const end = dest.slice(offset + src.length);
    return (start + src + end).substr(0, origDestLen);
  }

  // Casts the underlying lineAndCol object to a formatted message string,
  // highlighting `ranges`.
  function lineAndColumnToMessage(...ranges) {
    const lineAndCol = this;
    const {offset} = lineAndCol;
    const {repeatStr} = common;

    const sb = new StringBuffer();
    sb.append('Line ' + lineAndCol.lineNum + ', col ' + lineAndCol.colNum + ':\n');

    // An array of the previous, current, and next line numbers as strings of equal length.
    const lineNumbers = padNumbersToEqualLength([
      lineAndCol.prevLine == null ? 0 : lineAndCol.lineNum - 1,
      lineAndCol.lineNum,
      lineAndCol.nextLine == null ? 0 : lineAndCol.lineNum + 1,
    ]);

    // Helper for appending formatting input lines to the buffer.
    const appendLine = (num, content, prefix) => {
      sb.append(prefix + lineNumbers[num] + ' | ' + content + '\n');
    };

    // Include the previous line for context if possible.
    if (lineAndCol.prevLine != null) {
      appendLine(0, lineAndCol.prevLine, '  ');
    }
    // Line that the error occurred on.
    appendLine(1, lineAndCol.line, '> ');

    // Build up the line that points to the offset and possible indicates one or more ranges.
    // Start with a blank line, and indicate each range by overlaying a string of `~` chars.
    const lineLen = lineAndCol.line.length;
    let indicationLine = repeatStr(' ', lineLen + 1);
    for (let i = 0; i < ranges.length; ++i) {
      let startIdx = ranges[i][0];
      let endIdx = ranges[i][1];
      assert(startIdx >= 0 && startIdx <= endIdx, 'range start must be >= 0 and <= end');

      const lineStartOffset = offset - lineAndCol.colNum + 1;
      startIdx = Math.max(0, startIdx - lineStartOffset);
      endIdx = Math.min(endIdx - lineStartOffset, lineLen);

      indicationLine = strcpy(indicationLine, repeatStr('~', endIdx - startIdx), startIdx);
    }
    const gutterWidth = 2 + lineNumbers[1].length + 3;
    sb.append(repeatStr(' ', gutterWidth));
    indicationLine = strcpy(indicationLine, '^', lineAndCol.colNum - 1);
    sb.append(indicationLine.replace(/ +$/, '') + '\n');

    // Include the next line for context if possible.
    if (lineAndCol.nextLine != null) {
      appendLine(2, lineAndCol.nextLine, '  ');
    }
    return sb.contents();
  }

  // --------------------------------------------------------------------
  // Exports
  // --------------------------------------------------------------------

  let builtInRulesCallbacks = [];

  // Since Grammar.BuiltInRules is bootstrapped, most of Ohm can't directly depend it.
  // This function allows modules that do depend on the built-in rules to register a callback
  // that will be called later in the initialization process.
  function awaitBuiltInRules(cb) {
    builtInRulesCallbacks.push(cb);
  }

  function announceBuiltInRules(grammar) {
    builtInRulesCallbacks.forEach(cb => {
      cb(grammar);
    });
    builtInRulesCallbacks = null;
  }

  // Return an object with the line and column information for the given
  // offset in `str`.
  function getLineAndColumn(str, offset) {
    let lineNum = 1;
    let colNum = 1;

    let currOffset = 0;
    let lineStartOffset = 0;

    let nextLine = null;
    let prevLine = null;
    let prevLineStartOffset = -1;

    while (currOffset < offset) {
      const c = str.charAt(currOffset++);
      if (c === '\n') {
        lineNum++;
        colNum = 1;
        prevLineStartOffset = lineStartOffset;
        lineStartOffset = currOffset;
      } else if (c !== '\r') {
        colNum++;
      }
    }

    // Find the end of the target line.
    let lineEndOffset = str.indexOf('\n', lineStartOffset);
    if (lineEndOffset === -1) {
      lineEndOffset = str.length;
    } else {
      // Get the next line.
      const nextLineEndOffset = str.indexOf('\n', lineEndOffset + 1);
      nextLine =
        nextLineEndOffset === -1
          ? str.slice(lineEndOffset)
          : str.slice(lineEndOffset, nextLineEndOffset);
      // Strip leading and trailing EOL char(s).
      nextLine = nextLine.replace(/^\r?\n/, '').replace(/\r$/, '');
    }

    // Get the previous line.
    if (prevLineStartOffset >= 0) {
      // Strip trailing EOL char(s).
      prevLine = str.slice(prevLineStartOffset, lineStartOffset).replace(/\r?\n$/, '');
    }

    // Get the target line, stripping a trailing carriage return if necessary.
    const line = str.slice(lineStartOffset, lineEndOffset).replace(/\r$/, '');

    return {
      offset,
      lineNum,
      colNum,
      line,
      prevLine,
      nextLine,
      toString: lineAndColumnToMessage,
    };
  }

  // Return a nicely-formatted string describing the line and column for the
  // given offset in `str` highlighting `ranges`.
  function getLineAndColumnMessage(str, offset, ...ranges) {
    return getLineAndColumn(str, offset).toString(...ranges);
  }

  const uniqueId = (() => {
    let idCounter = 0;
    return prefix => '' + prefix + idCounter++;
  })();

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  class Interval {
    constructor(sourceString, startIdx, endIdx) {
      // Store the full source in a non-enumerable property, so that when
      // grammars and other objects are printed in the REPL, it's not
      // cluttered with multiple copies of the same long string.
      Object.defineProperty(this, '_sourceString', {
        value: sourceString,
        configurable: false,
        enumerable: false,
        writable: false,
      });
      this.startIdx = startIdx;
      this.endIdx = endIdx;
    }

    get sourceString() {
      return this._sourceString;
    }

    get contents() {
      if (this._contents === undefined) {
        this._contents = this.sourceString.slice(this.startIdx, this.endIdx);
      }
      return this._contents;
    }

    get length() {
      return this.endIdx - this.startIdx;
    }

    coverageWith(...intervals) {
      return Interval.coverage(...intervals, this);
    }

    collapsedLeft() {
      return new Interval(this.sourceString, this.startIdx, this.startIdx);
    }

    collapsedRight() {
      return new Interval(this.sourceString, this.endIdx, this.endIdx);
    }

    getLineAndColumn() {
      return getLineAndColumn(this.sourceString, this.startIdx);
    }

    getLineAndColumnMessage() {
      const range = [this.startIdx, this.endIdx];
      return getLineAndColumnMessage(this.sourceString, this.startIdx, range);
    }

    // Returns an array of 0, 1, or 2 intervals that represents the result of the
    // interval difference operation.
    minus(that) {
      if (this.sourceString !== that.sourceString) {
        throw intervalSourcesDontMatch();
      } else if (this.startIdx === that.startIdx && this.endIdx === that.endIdx) {
        // `this` and `that` are the same interval!
        return [];
      } else if (this.startIdx < that.startIdx && that.endIdx < this.endIdx) {
        // `that` splits `this` into two intervals
        return [
          new Interval(this.sourceString, this.startIdx, that.startIdx),
          new Interval(this.sourceString, that.endIdx, this.endIdx),
        ];
      } else if (this.startIdx < that.endIdx && that.endIdx < this.endIdx) {
        // `that` contains a prefix of `this`
        return [new Interval(this.sourceString, that.endIdx, this.endIdx)];
      } else if (this.startIdx < that.startIdx && that.startIdx < this.endIdx) {
        // `that` contains a suffix of `this`
        return [new Interval(this.sourceString, this.startIdx, that.startIdx)];
      } else {
        // `that` and `this` do not overlap
        return [this];
      }
    }

    // Returns a new Interval that has the same extent as this one, but which is relative
    // to `that`, an Interval that fully covers this one.
    relativeTo(that) {
      if (this.sourceString !== that.sourceString) {
        throw intervalSourcesDontMatch();
      }
      assert(
        this.startIdx >= that.startIdx && this.endIdx <= that.endIdx,
        'other interval does not cover this one'
      );
      return new Interval(
        this.sourceString,
        this.startIdx - that.startIdx,
        this.endIdx - that.startIdx
      );
    }

    // Returns a new Interval which contains the same contents as this one,
    // but with whitespace trimmed from both ends.
    trimmed() {
      const {contents} = this;
      const startIdx = this.startIdx + contents.match(/^\s*/)[0].length;
      const endIdx = this.endIdx - contents.match(/\s*$/)[0].length;
      return new Interval(this.sourceString, startIdx, endIdx);
    }

    subInterval(offset, len) {
      const newStartIdx = this.startIdx + offset;
      return new Interval(this.sourceString, newStartIdx, newStartIdx + len);
    }
  }

  Interval.coverage = function (firstInterval, ...intervals) {
    let {startIdx, endIdx} = firstInterval;
    for (const interval of intervals) {
      if (interval.sourceString !== firstInterval.sourceString) {
        throw intervalSourcesDontMatch();
      } else {
        startIdx = Math.min(startIdx, interval.startIdx);
        endIdx = Math.max(endIdx, interval.endIdx);
      }
    }
    return new Interval(firstInterval.sourceString, startIdx, endIdx);
  };

  const MAX_CHAR_CODE = 0xffff;
  const MAX_CODE_POINT = 0x10ffff;

  class InputStream {
    constructor(source) {
      this.source = source;
      this.pos = 0;
      this.examinedLength = 0;
    }

    atEnd() {
      const ans = this.pos >= this.source.length;
      this.examinedLength = Math.max(this.examinedLength, this.pos + 1);
      return ans;
    }

    next() {
      const ans = this.source[this.pos++];
      this.examinedLength = Math.max(this.examinedLength, this.pos);
      return ans;
    }

    nextCharCode() {
      const nextChar = this.next();
      return nextChar && nextChar.charCodeAt(0);
    }

    nextCodePoint() {
      const cp = this.source.slice(this.pos++).codePointAt(0);
      // If the code point is beyond plane 0, it takes up two characters.
      if (cp > MAX_CHAR_CODE) {
        this.pos += 1;
      }
      this.examinedLength = Math.max(this.examinedLength, this.pos);
      return cp;
    }

    matchString(s, optIgnoreCase) {
      let idx;
      if (optIgnoreCase) {
        /*
          Case-insensitive comparison is a tricky business. Some notable gotchas include the
          "Turkish I" problem (http://www.i18nguy.com/unicode/turkish-i18n.html) and the fact
          that the German Esszet (ß) turns into "SS" in upper case.

          This is intended to be a locale-invariant comparison, which means it may not obey
          locale-specific expectations (e.g. "i" => "İ").

          See also https://unicode.org/faq/casemap_charprop.html#casemap
         */
        for (idx = 0; idx < s.length; idx++) {
          const actual = this.next();
          const expected = s[idx];
          if (actual == null || actual.toUpperCase() !== expected.toUpperCase()) {
            return false;
          }
        }
        return true;
      }
      // Default is case-sensitive comparison.
      for (idx = 0; idx < s.length; idx++) {
        if (this.next() !== s[idx]) {
          return false;
        }
      }
      return true;
    }

    sourceSlice(startIdx, endIdx) {
      return this.source.slice(startIdx, endIdx);
    }

    interval(startIdx, optEndIdx) {
      return new Interval(this.source, startIdx, optEndIdx ? optEndIdx : this.pos);
    }
  }

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  class MatchResult {
    constructor(
      matcher,
      input,
      startExpr,
      cst,
      cstOffset,
      rightmostFailurePosition,
      optRecordedFailures
    ) {
      this.matcher = matcher;
      this.input = input;
      this.startExpr = startExpr;
      this._cst = cst;
      this._cstOffset = cstOffset;
      this._rightmostFailurePosition = rightmostFailurePosition;
      this._rightmostFailures = optRecordedFailures;

      if (this.failed()) {
        defineLazyProperty(this, 'message', function () {
          const detail = 'Expected ' + this.getExpectedText();
          return (
            getLineAndColumnMessage(this.input, this.getRightmostFailurePosition()) + detail
          );
        });
        defineLazyProperty(this, 'shortMessage', function () {
          const detail = 'expected ' + this.getExpectedText();
          const errorInfo = getLineAndColumn(
            this.input,
            this.getRightmostFailurePosition()
          );
          return 'Line ' + errorInfo.lineNum + ', col ' + errorInfo.colNum + ': ' + detail;
        });
      }
    }

    succeeded() {
      return !!this._cst;
    }

    failed() {
      return !this.succeeded();
    }

    getRightmostFailurePosition() {
      return this._rightmostFailurePosition;
    }

    getRightmostFailures() {
      if (!this._rightmostFailures) {
        this.matcher.setInput(this.input);
        const matchResultWithFailures = this.matcher._match(this.startExpr, {
          tracing: false,
          positionToRecordFailures: this.getRightmostFailurePosition(),
        });
        this._rightmostFailures = matchResultWithFailures.getRightmostFailures();
      }
      return this._rightmostFailures;
    }

    toString() {
      return this.succeeded()
        ? '[match succeeded]'
        : '[match failed at position ' + this.getRightmostFailurePosition() + ']';
    }

    // Return a string summarizing the expected contents of the input stream when
    // the match failure occurred.
    getExpectedText() {
      if (this.succeeded()) {
        throw new Error('cannot get expected text of a successful MatchResult');
      }

      const sb = new StringBuffer();
      let failures = this.getRightmostFailures();

      // Filter out the fluffy failures to make the default error messages more useful
      failures = failures.filter(failure => !failure.isFluffy());

      for (let idx = 0; idx < failures.length; idx++) {
        if (idx > 0) {
          if (idx === failures.length - 1) {
            sb.append(failures.length > 2 ? ', or ' : ' or ');
          } else {
            sb.append(', ');
          }
        }
        sb.append(failures[idx].toString());
      }
      return sb.contents();
    }

    getInterval() {
      const pos = this.getRightmostFailurePosition();
      return new Interval(this.input, pos, pos);
    }
  }

  class PosInfo {
    constructor() {
      this.applicationMemoKeyStack = []; // active applications at this position
      this.memo = {};
      this.maxExaminedLength = 0;
      this.maxRightmostFailureOffset = -1;
      this.currentLeftRecursion = undefined;
    }

    isActive(application) {
      return this.applicationMemoKeyStack.indexOf(application.toMemoKey()) >= 0;
    }

    enter(application) {
      this.applicationMemoKeyStack.push(application.toMemoKey());
    }

    exit() {
      this.applicationMemoKeyStack.pop();
    }

    startLeftRecursion(headApplication, memoRec) {
      memoRec.isLeftRecursion = true;
      memoRec.headApplication = headApplication;
      memoRec.nextLeftRecursion = this.currentLeftRecursion;
      this.currentLeftRecursion = memoRec;

      const {applicationMemoKeyStack} = this;
      const indexOfFirstInvolvedRule =
        applicationMemoKeyStack.indexOf(headApplication.toMemoKey()) + 1;
      const involvedApplicationMemoKeys = applicationMemoKeyStack.slice(
        indexOfFirstInvolvedRule
      );

      memoRec.isInvolved = function (applicationMemoKey) {
        return involvedApplicationMemoKeys.indexOf(applicationMemoKey) >= 0;
      };

      memoRec.updateInvolvedApplicationMemoKeys = function () {
        for (let idx = indexOfFirstInvolvedRule; idx < applicationMemoKeyStack.length; idx++) {
          const applicationMemoKey = applicationMemoKeyStack[idx];
          if (!this.isInvolved(applicationMemoKey)) {
            involvedApplicationMemoKeys.push(applicationMemoKey);
          }
        }
      };
    }

    endLeftRecursion() {
      this.currentLeftRecursion = this.currentLeftRecursion.nextLeftRecursion;
    }

    // Note: this method doesn't get called for the "head" of a left recursion -- for LR heads,
    // the memoized result (which starts out being a failure) is always used.
    shouldUseMemoizedResult(memoRec) {
      if (!memoRec.isLeftRecursion) {
        return true;
      }
      const {applicationMemoKeyStack} = this;
      for (let idx = 0; idx < applicationMemoKeyStack.length; idx++) {
        const applicationMemoKey = applicationMemoKeyStack[idx];
        if (memoRec.isInvolved(applicationMemoKey)) {
          return false;
        }
      }
      return true;
    }

    memoize(memoKey, memoRec) {
      this.memo[memoKey] = memoRec;
      this.maxExaminedLength = Math.max(this.maxExaminedLength, memoRec.examinedLength);
      this.maxRightmostFailureOffset = Math.max(
        this.maxRightmostFailureOffset,
        memoRec.rightmostFailureOffset
      );
      return memoRec;
    }

    clearObsoleteEntries(pos, invalidatedIdx) {
      if (pos + this.maxExaminedLength <= invalidatedIdx) {
        // Optimization: none of the rule applications that were memoized here examined the
        // interval of the input that changed, so nothing has to be invalidated.
        return;
      }

      const {memo} = this;
      this.maxExaminedLength = 0;
      this.maxRightmostFailureOffset = -1;
      Object.keys(memo).forEach(k => {
        const memoRec = memo[k];
        if (pos + memoRec.examinedLength > invalidatedIdx) {
          delete memo[k];
        } else {
          this.maxExaminedLength = Math.max(this.maxExaminedLength, memoRec.examinedLength);
          this.maxRightmostFailureOffset = Math.max(
            this.maxRightmostFailureOffset,
            memoRec.rightmostFailureOffset
          );
        }
      });
    }
  }

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  // Unicode characters that are used in the `toString` output.
  const BALLOT_X = '\u2717';
  const CHECK_MARK = '\u2713';
  const DOT_OPERATOR = '\u22C5';
  const RIGHTWARDS_DOUBLE_ARROW = '\u21D2';
  const SYMBOL_FOR_HORIZONTAL_TABULATION = '\u2409';
  const SYMBOL_FOR_LINE_FEED = '\u240A';
  const SYMBOL_FOR_CARRIAGE_RETURN = '\u240D';

  const Flags = {
    succeeded: 1 << 0,
    isRootNode: 1 << 1,
    isImplicitSpaces: 1 << 2,
    isMemoized: 1 << 3,
    isHeadOfLeftRecursion: 1 << 4,
    terminatesLR: 1 << 5,
  };

  function spaces(n) {
    return repeat(' ', n).join('');
  }

  // Return a string representation of a portion of `input` at offset `pos`.
  // The result will contain exactly `len` characters.
  function getInputExcerpt(input, pos, len) {
    const excerpt = asEscapedString(input.slice(pos, pos + len));

    // Pad the output if necessary.
    if (excerpt.length < len) {
      return excerpt + repeat(' ', len - excerpt.length).join('');
    }
    return excerpt;
  }

  function asEscapedString(obj) {
    if (typeof obj === 'string') {
      // Replace non-printable characters with visible symbols.
      return obj
        .replace(/ /g, DOT_OPERATOR)
        .replace(/\t/g, SYMBOL_FOR_HORIZONTAL_TABULATION)
        .replace(/\n/g, SYMBOL_FOR_LINE_FEED)
        .replace(/\r/g, SYMBOL_FOR_CARRIAGE_RETURN);
    }
    return String(obj);
  }

  // ----------------- Trace -----------------

  class Trace {
    constructor(input, pos1, pos2, expr, succeeded, bindings, optChildren) {
      this.input = input;
      this.pos = this.pos1 = pos1;
      this.pos2 = pos2;
      this.source = new Interval(input, pos1, pos2);
      this.expr = expr;
      this.bindings = bindings;
      this.children = optChildren || [];
      this.terminatingLREntry = null;

      this._flags = succeeded ? Flags.succeeded : 0;
    }

    get displayString() {
      return this.expr.toDisplayString();
    }

    clone() {
      return this.cloneWithExpr(this.expr);
    }

    cloneWithExpr(expr) {
      const ans = new Trace(
        this.input,
        this.pos,
        this.pos2,
        expr,
        this.succeeded,
        this.bindings,
        this.children
      );

      ans.isHeadOfLeftRecursion = this.isHeadOfLeftRecursion;
      ans.isImplicitSpaces = this.isImplicitSpaces;
      ans.isMemoized = this.isMemoized;
      ans.isRootNode = this.isRootNode;
      ans.terminatesLR = this.terminatesLR;
      ans.terminatingLREntry = this.terminatingLREntry;
      return ans;
    }

    // Record the trace information for the terminating condition of the LR loop.
    recordLRTermination(ruleBodyTrace, value) {
      this.terminatingLREntry = new Trace(
        this.input,
        this.pos,
        this.pos2,
        this.expr,
        false,
        [value],
        [ruleBodyTrace]
      );
      this.terminatingLREntry.terminatesLR = true;
    }

    // Recursively traverse this trace node and all its descendents, calling a visitor function
    // for each node that is visited. If `vistorObjOrFn` is an object, then its 'enter' property
    // is a function to call before visiting the children of a node, and its 'exit' property is
    // a function to call afterwards. If `visitorObjOrFn` is a function, it represents the 'enter'
    // function.
    //
    // The functions are called with three arguments: the Trace node, its parent Trace, and a number
    // representing the depth of the node in the tree. (The root node has depth 0.) `optThisArg`, if
    // specified, is the value to use for `this` when executing the visitor functions.
    walk(visitorObjOrFn, optThisArg) {
      let visitor = visitorObjOrFn;
      if (typeof visitor === 'function') {
        visitor = {enter: visitor};
      }

      function _walk(node, parent, depth) {
        let recurse = true;
        if (visitor.enter) {
          if (visitor.enter.call(optThisArg, node, parent, depth) === Trace.prototype.SKIP) {
            recurse = false;
          }
        }
        if (recurse) {
          node.children.forEach(child => {
            _walk(child, node, depth + 1);
          });
          if (visitor.exit) {
            visitor.exit.call(optThisArg, node, parent, depth);
          }
        }
      }
      if (this.isRootNode) {
        // Don't visit the root node itself, only its children.
        this.children.forEach(c => {
          _walk(c, null, 0);
        });
      } else {
        _walk(this, null, 0);
      }
    }

    // Return a string representation of the trace.
    // Sample:
    //     12⋅+⋅2⋅*⋅3 ✓ exp ⇒  "12"
    //     12⋅+⋅2⋅*⋅3   ✓ addExp (LR) ⇒  "12"
    //     12⋅+⋅2⋅*⋅3       ✗ addExp_plus
    toString() {
      const sb = new StringBuffer();
      this.walk((node, parent, depth) => {
        if (!node) {
          return this.SKIP;
        }
        const ctorName = node.expr.constructor.name;
        // Don't print anything for Alt nodes.
        if (ctorName === 'Alt') {
          return;
        }
        sb.append(getInputExcerpt(node.input, node.pos, 10) + spaces(depth * 2 + 1));
        sb.append((node.succeeded ? CHECK_MARK : BALLOT_X) + ' ' + node.displayString);
        if (node.isHeadOfLeftRecursion) {
          sb.append(' (LR)');
        }
        if (node.succeeded) {
          const contents = asEscapedString(node.source.contents);
          sb.append(' ' + RIGHTWARDS_DOUBLE_ARROW + '  ');
          sb.append(typeof contents === 'string' ? '"' + contents + '"' : contents);
        }
        sb.append('\n');
      });
      return sb.contents();
    }
  }

  // A value that can be returned from visitor functions to indicate that a
  // node should not be recursed into.
  Trace.prototype.SKIP = {};

  // For convenience, create a getter and setter for the boolean flags in `Flags`.
  Object.keys(Flags).forEach(name => {
    const mask = Flags[name];
    Object.defineProperty(Trace.prototype, name, {
      get() {
        return (this._flags & mask) !== 0;
      },
      set(val) {
        if (val) {
          this._flags |= mask;
        } else {
          this._flags &= ~mask;
        }
      },
    });
  });

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  /*
    Return true if we should skip spaces preceding this expression in a syntactic context.
  */
  PExpr.prototype.allowsSkippingPrecedingSpace = abstract('allowsSkippingPrecedingSpace');

  /*
    Generally, these are all first-order expressions and (with the exception of Apply)
    directly read from the input stream.
  */
  any.allowsSkippingPrecedingSpace =
    end.allowsSkippingPrecedingSpace =
    Apply.prototype.allowsSkippingPrecedingSpace =
    Terminal.prototype.allowsSkippingPrecedingSpace =
    Range.prototype.allowsSkippingPrecedingSpace =
    UnicodeChar.prototype.allowsSkippingPrecedingSpace =
      function () {
        return true;
      };

  /*
    Higher-order expressions that don't directly consume input.
  */
  Alt.prototype.allowsSkippingPrecedingSpace =
    Iter.prototype.allowsSkippingPrecedingSpace =
    Lex.prototype.allowsSkippingPrecedingSpace =
    Lookahead.prototype.allowsSkippingPrecedingSpace =
    Not.prototype.allowsSkippingPrecedingSpace =
    Param.prototype.allowsSkippingPrecedingSpace =
    Seq.prototype.allowsSkippingPrecedingSpace =
      function () {
        return false;
      };

  let BuiltInRules$1;

  awaitBuiltInRules(g => {
    BuiltInRules$1 = g;
  });

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  let lexifyCount;

  PExpr.prototype.assertAllApplicationsAreValid = function (ruleName, grammar) {
    lexifyCount = 0;
    this._assertAllApplicationsAreValid(ruleName, grammar);
  };

  PExpr.prototype._assertAllApplicationsAreValid = abstract(
    '_assertAllApplicationsAreValid'
  );

  any._assertAllApplicationsAreValid =
    end._assertAllApplicationsAreValid =
    Terminal.prototype._assertAllApplicationsAreValid =
    Range.prototype._assertAllApplicationsAreValid =
    Param.prototype._assertAllApplicationsAreValid =
    UnicodeChar.prototype._assertAllApplicationsAreValid =
      function (ruleName, grammar) {
        // no-op
      };

  Lex.prototype._assertAllApplicationsAreValid = function (ruleName, grammar) {
    lexifyCount++;
    this.expr._assertAllApplicationsAreValid(ruleName, grammar);
    lexifyCount--;
  };

  Alt.prototype._assertAllApplicationsAreValid = function (ruleName, grammar) {
    for (let idx = 0; idx < this.terms.length; idx++) {
      this.terms[idx]._assertAllApplicationsAreValid(ruleName, grammar);
    }
  };

  Seq.prototype._assertAllApplicationsAreValid = function (ruleName, grammar) {
    for (let idx = 0; idx < this.factors.length; idx++) {
      this.factors[idx]._assertAllApplicationsAreValid(ruleName, grammar);
    }
  };

  Iter.prototype._assertAllApplicationsAreValid =
    Not.prototype._assertAllApplicationsAreValid =
    Lookahead.prototype._assertAllApplicationsAreValid =
      function (ruleName, grammar) {
        this.expr._assertAllApplicationsAreValid(ruleName, grammar);
      };

  Apply.prototype._assertAllApplicationsAreValid = function (
    ruleName,
    grammar,
    skipSyntacticCheck = false
  ) {
    const ruleInfo = grammar.rules[this.ruleName];
    const isContextSyntactic = isSyntactic(ruleName) && lexifyCount === 0;

    // Make sure that the rule exists...
    if (!ruleInfo) {
      throw undeclaredRule(this.ruleName, grammar.name, this.source);
    }

    // ...and that this application is allowed
    if (!skipSyntacticCheck && isSyntactic(this.ruleName) && !isContextSyntactic) {
      throw applicationOfSyntacticRuleFromLexicalContext(this.ruleName, this);
    }

    // ...and that this application has the correct number of arguments.
    const actual = this.args.length;
    const expected = ruleInfo.formals.length;
    if (actual !== expected) {
      throw wrongNumberOfArguments(this.ruleName, expected, actual, this.source);
    }

    const isBuiltInApplySyntactic =
      BuiltInRules$1 && ruleInfo === BuiltInRules$1.rules.applySyntactic;
    const isBuiltInCaseInsensitive =
      BuiltInRules$1 && ruleInfo === BuiltInRules$1.rules.caseInsensitive;

    // If it's an application of 'caseInsensitive', ensure that the argument is a Terminal.
    if (isBuiltInCaseInsensitive) {
      if (!(this.args[0] instanceof Terminal)) {
        throw incorrectArgumentType('a Terminal (e.g. "abc")', this.args[0]);
      }
    }

    if (isBuiltInApplySyntactic) {
      const arg = this.args[0];
      if (!(arg instanceof Apply)) {
        throw incorrectArgumentType('a syntactic rule application', arg);
      }
      if (!isSyntactic(arg.ruleName)) {
        throw applySyntacticWithLexicalRuleApplication(arg);
      }
      if (isContextSyntactic) {
        throw unnecessaryExperimentalApplySyntactic(this);
      }
    }

    // ...and that all of the argument expressions only have valid applications and have arity 1.
    // If `this` is an application of the built-in applySyntactic rule, then its arg is
    // allowed (and expected) to be a syntactic rule, even if we're in a lexical context.
    this.args.forEach(arg => {
      arg._assertAllApplicationsAreValid(ruleName, grammar, isBuiltInApplySyntactic);
      if (arg.getArity() !== 1) {
        throw invalidParameter(this.ruleName, arg);
      }
    });
  };

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  PExpr.prototype.assertChoicesHaveUniformArity = abstract(
    'assertChoicesHaveUniformArity'
  );

  any.assertChoicesHaveUniformArity =
    end.assertChoicesHaveUniformArity =
    Terminal.prototype.assertChoicesHaveUniformArity =
    Range.prototype.assertChoicesHaveUniformArity =
    Param.prototype.assertChoicesHaveUniformArity =
    Lex.prototype.assertChoicesHaveUniformArity =
    UnicodeChar.prototype.assertChoicesHaveUniformArity =
      function (ruleName) {
        // no-op
      };

  Alt.prototype.assertChoicesHaveUniformArity = function (ruleName) {
    if (this.terms.length === 0) {
      return;
    }
    const arity = this.terms[0].getArity();
    for (let idx = 0; idx < this.terms.length; idx++) {
      const term = this.terms[idx];
      term.assertChoicesHaveUniformArity();
      const otherArity = term.getArity();
      if (arity !== otherArity) {
        throw inconsistentArity(ruleName, arity, otherArity, term);
      }
    }
  };

  Extend.prototype.assertChoicesHaveUniformArity = function (ruleName) {
    // Extend is a special case of Alt that's guaranteed to have exactly two
    // cases: [extensions, origBody].
    const actualArity = this.terms[0].getArity();
    const expectedArity = this.terms[1].getArity();
    if (actualArity !== expectedArity) {
      throw inconsistentArity(ruleName, expectedArity, actualArity, this.terms[0]);
    }
  };

  Seq.prototype.assertChoicesHaveUniformArity = function (ruleName) {
    for (let idx = 0; idx < this.factors.length; idx++) {
      this.factors[idx].assertChoicesHaveUniformArity(ruleName);
    }
  };

  Iter.prototype.assertChoicesHaveUniformArity = function (ruleName) {
    this.expr.assertChoicesHaveUniformArity(ruleName);
  };

  Not.prototype.assertChoicesHaveUniformArity = function (ruleName) {
    // no-op (not required b/c the nested expr doesn't show up in the CST)
  };

  Lookahead.prototype.assertChoicesHaveUniformArity = function (ruleName) {
    this.expr.assertChoicesHaveUniformArity(ruleName);
  };

  Apply.prototype.assertChoicesHaveUniformArity = function (ruleName) {
    // The arities of the parameter expressions is required to be 1 by
    // `assertAllApplicationsAreValid()`.
  };

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  PExpr.prototype.assertIteratedExprsAreNotNullable = abstract(
    'assertIteratedExprsAreNotNullable'
  );

  any.assertIteratedExprsAreNotNullable =
    end.assertIteratedExprsAreNotNullable =
    Terminal.prototype.assertIteratedExprsAreNotNullable =
    Range.prototype.assertIteratedExprsAreNotNullable =
    Param.prototype.assertIteratedExprsAreNotNullable =
    UnicodeChar.prototype.assertIteratedExprsAreNotNullable =
      function (grammar) {
        // no-op
      };

  Alt.prototype.assertIteratedExprsAreNotNullable = function (grammar) {
    for (let idx = 0; idx < this.terms.length; idx++) {
      this.terms[idx].assertIteratedExprsAreNotNullable(grammar);
    }
  };

  Seq.prototype.assertIteratedExprsAreNotNullable = function (grammar) {
    for (let idx = 0; idx < this.factors.length; idx++) {
      this.factors[idx].assertIteratedExprsAreNotNullable(grammar);
    }
  };

  Iter.prototype.assertIteratedExprsAreNotNullable = function (grammar) {
    // Note: this is the implementation of this method for `Star` and `Plus` expressions.
    // It is overridden for `Opt` below.
    this.expr.assertIteratedExprsAreNotNullable(grammar);
    if (this.expr.isNullable(grammar)) {
      throw kleeneExprHasNullableOperand(this, []);
    }
  };

  Opt.prototype.assertIteratedExprsAreNotNullable =
    Not.prototype.assertIteratedExprsAreNotNullable =
    Lookahead.prototype.assertIteratedExprsAreNotNullable =
    Lex.prototype.assertIteratedExprsAreNotNullable =
      function (grammar) {
        this.expr.assertIteratedExprsAreNotNullable(grammar);
      };

  Apply.prototype.assertIteratedExprsAreNotNullable = function (grammar) {
    this.args.forEach(arg => {
      arg.assertIteratedExprsAreNotNullable(grammar);
    });
  };

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  class Node {
    constructor(matchLength) {
      this.matchLength = matchLength;
    }

    get ctorName() {
      throw new Error('subclass responsibility');
    }

    numChildren() {
      return this.children ? this.children.length : 0;
    }

    childAt(idx) {
      if (this.children) {
        return this.children[idx];
      }
    }

    indexOfChild(arg) {
      return this.children.indexOf(arg);
    }

    hasChildren() {
      return this.numChildren() > 0;
    }

    hasNoChildren() {
      return !this.hasChildren();
    }

    onlyChild() {
      if (this.numChildren() !== 1) {
        throw new Error(
          'cannot get only child of a node of type ' +
            this.ctorName +
            ' (it has ' +
            this.numChildren() +
            ' children)'
        );
      } else {
        return this.firstChild();
      }
    }

    firstChild() {
      if (this.hasNoChildren()) {
        throw new Error(
          'cannot get first child of a ' + this.ctorName + ' node, which has no children'
        );
      } else {
        return this.childAt(0);
      }
    }

    lastChild() {
      if (this.hasNoChildren()) {
        throw new Error(
          'cannot get last child of a ' + this.ctorName + ' node, which has no children'
        );
      } else {
        return this.childAt(this.numChildren() - 1);
      }
    }

    childBefore(child) {
      const childIdx = this.indexOfChild(child);
      if (childIdx < 0) {
        throw new Error('Node.childBefore() called w/ an argument that is not a child');
      } else if (childIdx === 0) {
        throw new Error('cannot get child before first child');
      } else {
        return this.childAt(childIdx - 1);
      }
    }

    childAfter(child) {
      const childIdx = this.indexOfChild(child);
      if (childIdx < 0) {
        throw new Error('Node.childAfter() called w/ an argument that is not a child');
      } else if (childIdx === this.numChildren() - 1) {
        throw new Error('cannot get child after last child');
      } else {
        return this.childAt(childIdx + 1);
      }
    }

    isTerminal() {
      return false;
    }

    isNonterminal() {
      return false;
    }

    isIteration() {
      return false;
    }

    isOptional() {
      return false;
    }
  }

  // Terminals

  class TerminalNode extends Node {
    get ctorName() {
      return '_terminal';
    }

    isTerminal() {
      return true;
    }

    get primitiveValue() {
      throw new Error('The `primitiveValue` property was removed in Ohm v17.');
    }
  }

  // Nonterminals

  class NonterminalNode extends Node {
    constructor(ruleName, children, childOffsets, matchLength) {
      super(matchLength);
      this.ruleName = ruleName;
      this.children = children;
      this.childOffsets = childOffsets;
    }

    get ctorName() {
      return this.ruleName;
    }

    isNonterminal() {
      return true;
    }

    isLexical() {
      return isLexical(this.ctorName);
    }

    isSyntactic() {
      return isSyntactic(this.ctorName);
    }
  }

  // Iterations

  class IterationNode extends Node {
    constructor(children, childOffsets, matchLength, isOptional) {
      super(matchLength);
      this.children = children;
      this.childOffsets = childOffsets;
      this.optional = isOptional;
    }

    get ctorName() {
      return '_iter';
    }

    isIteration() {
      return true;
    }

    isOptional() {
      return this.optional;
    }
  }

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  /*
    Evaluate the expression and return `true` if it succeeds, `false` otherwise. This method should
    only be called directly by `State.prototype.eval(expr)`, which also updates the data structures
    that are used for tracing. (Making those updates in a method of `State` enables the trace-specific
    data structures to be "secrets" of that class, which is good for modularity.)

    The contract of this method is as follows:
    * When the return value is `true`,
      - the state object will have `expr.getArity()` more bindings than it did before the call.
    * When the return value is `false`,
      - the state object may have more bindings than it did before the call, and
      - its input stream's position may be anywhere.

    Note that `State.prototype.eval(expr)`, unlike this method, guarantees that neither the state
    object's bindings nor its input stream's position will change if the expression fails to match.
  */
  PExpr.prototype.eval = abstract('eval'); // function(state) { ... }

  any.eval = function (state) {
    const {inputStream} = state;
    const origPos = inputStream.pos;
    const cp = inputStream.nextCodePoint();
    if (cp !== undefined) {
      state.pushBinding(new TerminalNode(String.fromCodePoint(cp).length), origPos);
      return true;
    } else {
      state.processFailure(origPos, this);
      return false;
    }
  };

  end.eval = function (state) {
    const {inputStream} = state;
    const origPos = inputStream.pos;
    if (inputStream.atEnd()) {
      state.pushBinding(new TerminalNode(0), origPos);
      return true;
    } else {
      state.processFailure(origPos, this);
      return false;
    }
  };

  Terminal.prototype.eval = function (state) {
    const {inputStream} = state;
    const origPos = inputStream.pos;
    if (!inputStream.matchString(this.obj)) {
      state.processFailure(origPos, this);
      return false;
    } else {
      state.pushBinding(new TerminalNode(this.obj.length), origPos);
      return true;
    }
  };

  Range.prototype.eval = function (state) {
    const {inputStream} = state;
    const origPos = inputStream.pos;

    // A range can operate in one of two modes: matching a single, 16-bit _code unit_,
    // or matching a _code point_. (Code points over 0xFFFF take up two 16-bit code units.)
    const cp = this.matchCodePoint ? inputStream.nextCodePoint() : inputStream.nextCharCode();

    // Always compare by code point value to get the correct result in all scenarios.
    // Note that for strings of length 1, codePointAt(0) and charPointAt(0) are equivalent.
    if (cp !== undefined && this.from.codePointAt(0) <= cp && cp <= this.to.codePointAt(0)) {
      state.pushBinding(new TerminalNode(String.fromCodePoint(cp).length), origPos);
      return true;
    } else {
      state.processFailure(origPos, this);
      return false;
    }
  };

  Param.prototype.eval = function (state) {
    return state.eval(state.currentApplication().args[this.index]);
  };

  Lex.prototype.eval = function (state) {
    state.enterLexifiedContext();
    const ans = state.eval(this.expr);
    state.exitLexifiedContext();
    return ans;
  };

  Alt.prototype.eval = function (state) {
    for (let idx = 0; idx < this.terms.length; idx++) {
      if (state.eval(this.terms[idx])) {
        return true;
      }
    }
    return false;
  };

  Seq.prototype.eval = function (state) {
    for (let idx = 0; idx < this.factors.length; idx++) {
      const factor = this.factors[idx];
      if (!state.eval(factor)) {
        return false;
      }
    }
    return true;
  };

  Iter.prototype.eval = function (state) {
    const {inputStream} = state;
    const origPos = inputStream.pos;
    const arity = this.getArity();
    const cols = [];
    const colOffsets = [];
    while (cols.length < arity) {
      cols.push([]);
      colOffsets.push([]);
    }

    let numMatches = 0;
    let prevPos = origPos;
    let idx;
    while (numMatches < this.maxNumMatches && state.eval(this.expr)) {
      if (inputStream.pos === prevPos) {
        throw kleeneExprHasNullableOperand(this, state._applicationStack);
      }
      prevPos = inputStream.pos;
      numMatches++;
      const row = state._bindings.splice(state._bindings.length - arity, arity);
      const rowOffsets = state._bindingOffsets.splice(
        state._bindingOffsets.length - arity,
        arity
      );
      for (idx = 0; idx < row.length; idx++) {
        cols[idx].push(row[idx]);
        colOffsets[idx].push(rowOffsets[idx]);
      }
    }
    if (numMatches < this.minNumMatches) {
      return false;
    }
    let offset = state.posToOffset(origPos);
    let matchLength = 0;
    if (numMatches > 0) {
      const lastCol = cols[arity - 1];
      const lastColOffsets = colOffsets[arity - 1];

      const endOffset =
        lastColOffsets[lastColOffsets.length - 1] + lastCol[lastCol.length - 1].matchLength;
      offset = colOffsets[0][0];
      matchLength = endOffset - offset;
    }
    const isOptional = this instanceof Opt;
    for (idx = 0; idx < cols.length; idx++) {
      state._bindings.push(
        new IterationNode(cols[idx], colOffsets[idx], matchLength, isOptional)
      );
      state._bindingOffsets.push(offset);
    }
    return true;
  };

  Not.prototype.eval = function (state) {
    /*
      TODO:
      - Right now we're just throwing away all of the failures that happen inside a `not`, and
        recording `this` as a failed expression.
      - Double negation should be equivalent to lookahead, but that's not the case right now wrt
        failures. E.g., ~~'foo' produces a failure for ~~'foo', but maybe it should produce
        a failure for 'foo' instead.
    */

    const {inputStream} = state;
    const origPos = inputStream.pos;
    state.pushFailuresInfo();

    const ans = state.eval(this.expr);

    state.popFailuresInfo();
    if (ans) {
      state.processFailure(origPos, this);
      return false;
    }

    inputStream.pos = origPos;
    return true;
  };

  Lookahead.prototype.eval = function (state) {
    const {inputStream} = state;
    const origPos = inputStream.pos;
    if (state.eval(this.expr)) {
      inputStream.pos = origPos;
      return true;
    } else {
      return false;
    }
  };

  Apply.prototype.eval = function (state) {
    const caller = state.currentApplication();
    const actuals = caller ? caller.args : [];
    const app = this.substituteParams(actuals);

    const posInfo = state.getCurrentPosInfo();
    if (posInfo.isActive(app)) {
      // This rule is already active at this position, i.e., it is left-recursive.
      return app.handleCycle(state);
    }

    const memoKey = app.toMemoKey();
    const memoRec = posInfo.memo[memoKey];

    if (memoRec && posInfo.shouldUseMemoizedResult(memoRec)) {
      if (state.hasNecessaryInfo(memoRec)) {
        return state.useMemoizedResult(state.inputStream.pos, memoRec);
      }
      delete posInfo.memo[memoKey];
    }
    return app.reallyEval(state);
  };

  Apply.prototype.handleCycle = function (state) {
    const posInfo = state.getCurrentPosInfo();
    const {currentLeftRecursion} = posInfo;
    const memoKey = this.toMemoKey();
    let memoRec = posInfo.memo[memoKey];

    if (currentLeftRecursion && currentLeftRecursion.headApplication.toMemoKey() === memoKey) {
      // We already know about this left recursion, but it's possible there are "involved
      // applications" that we don't already know about, so...
      memoRec.updateInvolvedApplicationMemoKeys();
    } else if (!memoRec) {
      // New left recursion detected! Memoize a failure to try to get a seed parse.
      memoRec = posInfo.memoize(memoKey, {
        matchLength: 0,
        examinedLength: 0,
        value: false,
        rightmostFailureOffset: -1,
      });
      posInfo.startLeftRecursion(this, memoRec);
    }
    return state.useMemoizedResult(state.inputStream.pos, memoRec);
  };

  Apply.prototype.reallyEval = function (state) {
    const {inputStream} = state;
    const origPos = inputStream.pos;
    const origPosInfo = state.getCurrentPosInfo();
    const ruleInfo = state.grammar.rules[this.ruleName];
    const {body} = ruleInfo;
    const {description} = ruleInfo;

    state.enterApplication(origPosInfo, this);

    if (description) {
      state.pushFailuresInfo();
    }

    // Reset the input stream's examinedLength property so that we can track
    // the examined length of this particular application.
    const origInputStreamExaminedLength = inputStream.examinedLength;
    inputStream.examinedLength = 0;

    let value = this.evalOnce(body, state);
    const currentLR = origPosInfo.currentLeftRecursion;
    const memoKey = this.toMemoKey();
    const isHeadOfLeftRecursion = currentLR && currentLR.headApplication.toMemoKey() === memoKey;
    let memoRec;

    if (state.doNotMemoize) {
      state.doNotMemoize = false;
    } else if (isHeadOfLeftRecursion) {
      value = this.growSeedResult(body, state, origPos, currentLR, value);
      origPosInfo.endLeftRecursion();
      memoRec = currentLR;
      memoRec.examinedLength = inputStream.examinedLength - origPos;
      memoRec.rightmostFailureOffset = state._getRightmostFailureOffset();
      origPosInfo.memoize(memoKey, memoRec); // updates origPosInfo's maxExaminedLength
    } else if (!currentLR || !currentLR.isInvolved(memoKey)) {
      // This application is not involved in left recursion, so it's ok to memoize it.
      memoRec = origPosInfo.memoize(memoKey, {
        matchLength: inputStream.pos - origPos,
        examinedLength: inputStream.examinedLength - origPos,
        value,
        failuresAtRightmostPosition: state.cloneRecordedFailures(),
        rightmostFailureOffset: state._getRightmostFailureOffset(),
      });
    }
    const succeeded = !!value;

    if (description) {
      state.popFailuresInfo();
      if (!succeeded) {
        state.processFailure(origPos, this);
      }
      if (memoRec) {
        memoRec.failuresAtRightmostPosition = state.cloneRecordedFailures();
        memoRec.rightmostFailureOffset = state._getRightmostFailureOffset();
      }
    }

    // Record trace information in the memo table, so that it is available if the memoized result
    // is used later.
    if (state.isTracing() && memoRec) {
      const entry = state.getTraceEntry(origPos, this, succeeded, succeeded ? [value] : []);
      if (isHeadOfLeftRecursion) {
        assert(entry.terminatingLREntry != null || !succeeded);
        entry.isHeadOfLeftRecursion = true;
      }
      memoRec.traceEntry = entry;
    }

    // Fix the input stream's examinedLength -- it should be the maximum examined length
    // across all applications, not just this one.
    inputStream.examinedLength = Math.max(
      inputStream.examinedLength,
      origInputStreamExaminedLength
    );

    state.exitApplication(origPosInfo, value);

    return succeeded;
  };

  Apply.prototype.evalOnce = function (expr, state) {
    const {inputStream} = state;
    const origPos = inputStream.pos;

    if (state.eval(expr)) {
      const arity = expr.getArity();
      const bindings = state._bindings.splice(state._bindings.length - arity, arity);
      const offsets = state._bindingOffsets.splice(state._bindingOffsets.length - arity, arity);
      const matchLength = inputStream.pos - origPos;
      return new NonterminalNode(this.ruleName, bindings, offsets, matchLength);
    } else {
      return false;
    }
  };

  Apply.prototype.growSeedResult = function (body, state, origPos, lrMemoRec, newValue) {
    if (!newValue) {
      return false;
    }

    const {inputStream} = state;

    while (true) {
      lrMemoRec.matchLength = inputStream.pos - origPos;
      lrMemoRec.value = newValue;
      lrMemoRec.failuresAtRightmostPosition = state.cloneRecordedFailures();

      if (state.isTracing()) {
        // Before evaluating the body again, add a trace node for this application to the memo entry.
        // Its only child is a copy of the trace node from `newValue`, which will always be the last
        // element in `state.trace`.
        const seedTrace = state.trace[state.trace.length - 1];
        lrMemoRec.traceEntry = new Trace(
          state.input,
          origPos,
          inputStream.pos,
          this,
          true,
          [newValue],
          [seedTrace.clone()]
        );
      }
      inputStream.pos = origPos;
      newValue = this.evalOnce(body, state);
      if (inputStream.pos - origPos <= lrMemoRec.matchLength) {
        break;
      }
      if (state.isTracing()) {
        state.trace.splice(-2, 1); // Drop the trace for the old seed.
      }
    }
    if (state.isTracing()) {
      // The last entry is for an unused result -- pop it and save it in the "real" entry.
      lrMemoRec.traceEntry.recordLRTermination(state.trace.pop(), newValue);
    }
    inputStream.pos = origPos + lrMemoRec.matchLength;
    return lrMemoRec.value;
  };

  UnicodeChar.prototype.eval = function (state) {
    const {inputStream} = state;
    const origPos = inputStream.pos;
    const cp = inputStream.nextCodePoint();
    if (cp !== undefined && cp <= MAX_CODE_POINT) {
      const ch = String.fromCodePoint(cp);
      if (this.pattern.test(ch)) {
        state.pushBinding(new TerminalNode(ch.length), origPos);
        return true;
      }
    }
    state.processFailure(origPos, this);
    return false;
  };

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  PExpr.prototype.getArity = abstract('getArity');

  any.getArity =
    end.getArity =
    Terminal.prototype.getArity =
    Range.prototype.getArity =
    Param.prototype.getArity =
    Apply.prototype.getArity =
    UnicodeChar.prototype.getArity =
      function () {
        return 1;
      };

  Alt.prototype.getArity = function () {
    // This is ok b/c all terms must have the same arity -- this property is
    // checked by the Grammar constructor.
    return this.terms.length === 0 ? 0 : this.terms[0].getArity();
  };

  Seq.prototype.getArity = function () {
    let arity = 0;
    for (let idx = 0; idx < this.factors.length; idx++) {
      arity += this.factors[idx].getArity();
    }
    return arity;
  };

  Iter.prototype.getArity = function () {
    return this.expr.getArity();
  };

  Not.prototype.getArity = function () {
    return 0;
  };

  Lookahead.prototype.getArity = Lex.prototype.getArity = function () {
    return this.expr.getArity();
  };

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  function getMetaInfo(expr, grammarInterval) {
    const metaInfo = {};
    if (expr.source && grammarInterval) {
      const adjusted = expr.source.relativeTo(grammarInterval);
      metaInfo.sourceInterval = [adjusted.startIdx, adjusted.endIdx];
    }
    return metaInfo;
  }

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  PExpr.prototype.outputRecipe = abstract('outputRecipe');

  any.outputRecipe = function (formals, grammarInterval) {
    return ['any', getMetaInfo(this, grammarInterval)];
  };

  end.outputRecipe = function (formals, grammarInterval) {
    return ['end', getMetaInfo(this, grammarInterval)];
  };

  Terminal.prototype.outputRecipe = function (formals, grammarInterval) {
    return ['terminal', getMetaInfo(this, grammarInterval), this.obj];
  };

  Range.prototype.outputRecipe = function (formals, grammarInterval) {
    return ['range', getMetaInfo(this, grammarInterval), this.from, this.to];
  };

  Param.prototype.outputRecipe = function (formals, grammarInterval) {
    return ['param', getMetaInfo(this, grammarInterval), this.index];
  };

  Alt.prototype.outputRecipe = function (formals, grammarInterval) {
    return ['alt', getMetaInfo(this, grammarInterval)].concat(
      this.terms.map(term => term.outputRecipe(formals, grammarInterval))
    );
  };

  Extend.prototype.outputRecipe = function (formals, grammarInterval) {
    const extension = this.terms[0]; // [extension, original]
    return extension.outputRecipe(formals, grammarInterval);
  };

  Splice.prototype.outputRecipe = function (formals, grammarInterval) {
    const beforeTerms = this.terms.slice(0, this.expansionPos);
    const afterTerms = this.terms.slice(this.expansionPos + 1);
    return [
      'splice',
      getMetaInfo(this, grammarInterval),
      beforeTerms.map(term => term.outputRecipe(formals, grammarInterval)),
      afterTerms.map(term => term.outputRecipe(formals, grammarInterval)),
    ];
  };

  Seq.prototype.outputRecipe = function (formals, grammarInterval) {
    return ['seq', getMetaInfo(this, grammarInterval)].concat(
      this.factors.map(factor => factor.outputRecipe(formals, grammarInterval))
    );
  };

  Star.prototype.outputRecipe =
    Plus.prototype.outputRecipe =
    Opt.prototype.outputRecipe =
    Not.prototype.outputRecipe =
    Lookahead.prototype.outputRecipe =
    Lex.prototype.outputRecipe =
      function (formals, grammarInterval) {
        return [
          this.constructor.name.toLowerCase(),
          getMetaInfo(this, grammarInterval),
          this.expr.outputRecipe(formals, grammarInterval),
        ];
      };

  Apply.prototype.outputRecipe = function (formals, grammarInterval) {
    return [
      'app',
      getMetaInfo(this, grammarInterval),
      this.ruleName,
      this.args.map(arg => arg.outputRecipe(formals, grammarInterval)),
    ];
  };

  UnicodeChar.prototype.outputRecipe = function (formals, grammarInterval) {
    return ['unicodeChar', getMetaInfo(this, grammarInterval), this.categoryOrProp];
  };

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  /*
    Called at grammar creation time to rewrite a rule body, replacing each reference to a formal
    parameter with a `Param` node. Returns a PExpr -- either a new one, or the original one if
    it was modified in place.
  */
  PExpr.prototype.introduceParams = abstract('introduceParams');

  any.introduceParams =
    end.introduceParams =
    Terminal.prototype.introduceParams =
    Range.prototype.introduceParams =
    Param.prototype.introduceParams =
    UnicodeChar.prototype.introduceParams =
      function (formals) {
        return this;
      };

  Alt.prototype.introduceParams = function (formals) {
    this.terms.forEach((term, idx, terms) => {
      terms[idx] = term.introduceParams(formals);
    });
    return this;
  };

  Seq.prototype.introduceParams = function (formals) {
    this.factors.forEach((factor, idx, factors) => {
      factors[idx] = factor.introduceParams(formals);
    });
    return this;
  };

  Iter.prototype.introduceParams =
    Not.prototype.introduceParams =
    Lookahead.prototype.introduceParams =
    Lex.prototype.introduceParams =
      function (formals) {
        this.expr = this.expr.introduceParams(formals);
        return this;
      };

  Apply.prototype.introduceParams = function (formals) {
    const index = formals.indexOf(this.ruleName);
    if (index >= 0) {
      if (this.args.length > 0) {
        // TODO: Should this be supported? See issue #64.
        throw new Error('Parameterized rules cannot be passed as arguments to another rule.');
      }
      return new Param(index).withSource(this.source);
    } else {
      this.args.forEach((arg, idx, args) => {
        args[idx] = arg.introduceParams(formals);
      });
      return this;
    }
  };

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  // Returns `true` if this parsing expression may accept without consuming any input.
  PExpr.prototype.isNullable = function (grammar) {
    return this._isNullable(grammar, Object.create(null));
  };

  PExpr.prototype._isNullable = abstract('_isNullable');

  any._isNullable =
    Range.prototype._isNullable =
    Param.prototype._isNullable =
    Plus.prototype._isNullable =
    UnicodeChar.prototype._isNullable =
      function (grammar, memo) {
        return false;
      };

  end._isNullable = function (grammar, memo) {
    return true;
  };

  Terminal.prototype._isNullable = function (grammar, memo) {
    if (typeof this.obj === 'string') {
      // This is an over-simplification: it's only correct if the input is a string. If it's an array
      // or an object, then the empty string parsing expression is not nullable.
      return this.obj === '';
    } else {
      return false;
    }
  };

  Alt.prototype._isNullable = function (grammar, memo) {
    return this.terms.length === 0 || this.terms.some(term => term._isNullable(grammar, memo));
  };

  Seq.prototype._isNullable = function (grammar, memo) {
    return this.factors.every(factor => factor._isNullable(grammar, memo));
  };

  Star.prototype._isNullable =
    Opt.prototype._isNullable =
    Not.prototype._isNullable =
    Lookahead.prototype._isNullable =
      function (grammar, memo) {
        return true;
      };

  Lex.prototype._isNullable = function (grammar, memo) {
    return this.expr._isNullable(grammar, memo);
  };

  Apply.prototype._isNullable = function (grammar, memo) {
    const key = this.toMemoKey();
    if (!Object.prototype.hasOwnProperty.call(memo, key)) {
      const {body} = grammar.rules[this.ruleName];
      const inlined = body.substituteParams(this.args);
      memo[key] = false; // Prevent infinite recursion for recursive rules.
      memo[key] = inlined._isNullable(grammar, memo);
    }
    return memo[key];
  };

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  /*
    Returns a PExpr that results from recursively replacing every formal parameter (i.e., instance
    of `Param`) inside this PExpr with its actual value from `actuals` (an Array).

    The receiver must not be modified; a new PExpr must be returned if any replacement is necessary.
  */
  // function(actuals) { ... }
  PExpr.prototype.substituteParams = abstract('substituteParams');

  any.substituteParams =
    end.substituteParams =
    Terminal.prototype.substituteParams =
    Range.prototype.substituteParams =
    UnicodeChar.prototype.substituteParams =
      function (actuals) {
        return this;
      };

  Param.prototype.substituteParams = function (actuals) {
    return checkNotNull(actuals[this.index]);
  };

  Alt.prototype.substituteParams = function (actuals) {
    return new Alt(this.terms.map(term => term.substituteParams(actuals)));
  };

  Seq.prototype.substituteParams = function (actuals) {
    return new Seq(this.factors.map(factor => factor.substituteParams(actuals)));
  };

  Iter.prototype.substituteParams =
    Not.prototype.substituteParams =
    Lookahead.prototype.substituteParams =
    Lex.prototype.substituteParams =
      function (actuals) {
        return new this.constructor(this.expr.substituteParams(actuals));
      };

  Apply.prototype.substituteParams = function (actuals) {
    if (this.args.length === 0) {
      // Avoid making a copy of this application, as an optimization
      return this;
    } else {
      const args = this.args.map(arg => arg.substituteParams(actuals));
      return new Apply(this.ruleName, args);
    }
  };

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  function isRestrictedJSIdentifier(str) {
    return /^[a-zA-Z_$][0-9a-zA-Z_$]*$/.test(str);
  }

  function resolveDuplicatedNames(argumentNameList) {
    // `count` is used to record the number of times each argument name occurs in the list,
    // this is useful for checking duplicated argument name. It maps argument names to ints.
    const count = Object.create(null);
    argumentNameList.forEach(argName => {
      count[argName] = (count[argName] || 0) + 1;
    });

    // Append subscripts ('_1', '_2', ...) to duplicate argument names.
    Object.keys(count).forEach(dupArgName => {
      if (count[dupArgName] <= 1) {
        return;
      }

      // This name shows up more than once, so add subscripts.
      let subscript = 1;
      argumentNameList.forEach((argName, idx) => {
        if (argName === dupArgName) {
          argumentNameList[idx] = argName + '_' + subscript++;
        }
      });
    });
  }

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  /*
    Returns a list of strings that will be used as the default argument names for its receiver
    (a pexpr) in a semantic action. This is used exclusively by the Semantics Editor.

    `firstArgIndex` is the 1-based index of the first argument name that will be generated for this
    pexpr. It enables us to name arguments positionally, e.g., if the second argument is a
    non-alphanumeric terminal like "+", it will be named '$2'.

    `noDupCheck` is true if the caller of `toArgumentNameList` is not a top level caller. It enables
    us to avoid nested duplication subscripts appending, e.g., '_1_1', '_1_2', by only checking
    duplicates at the top level.

    Here is a more elaborate example that illustrates how this method works:
    `(a "+" b).toArgumentNameList(1)` evaluates to `['a', '$2', 'b']` with the following recursive
    calls:

      (a).toArgumentNameList(1) -> ['a'],
      ("+").toArgumentNameList(2) -> ['$2'],
      (b).toArgumentNameList(3) -> ['b']

    Notes:
    * This method must only be called on well-formed expressions, e.g., the receiver must
      not have any Alt sub-expressions with inconsistent arities.
    * e.getArity() === e.toArgumentNameList(1).length
  */
  // function(firstArgIndex, noDupCheck) { ... }
  PExpr.prototype.toArgumentNameList = abstract('toArgumentNameList');

  any.toArgumentNameList = function (firstArgIndex, noDupCheck) {
    return ['any'];
  };

  end.toArgumentNameList = function (firstArgIndex, noDupCheck) {
    return ['end'];
  };

  Terminal.prototype.toArgumentNameList = function (firstArgIndex, noDupCheck) {
    if (typeof this.obj === 'string' && /^[_a-zA-Z0-9]+$/.test(this.obj)) {
      // If this terminal is a valid suffix for a JS identifier, just prepend it with '_'
      return ['_' + this.obj];
    } else {
      // Otherwise, name it positionally.
      return ['$' + firstArgIndex];
    }
  };

  Range.prototype.toArgumentNameList = function (firstArgIndex, noDupCheck) {
    let argName = this.from + '_to_' + this.to;
    // If the `argName` is not valid then try to prepend a `_`.
    if (!isRestrictedJSIdentifier(argName)) {
      argName = '_' + argName;
    }
    // If the `argName` still not valid after prepending a `_`, then name it positionally.
    if (!isRestrictedJSIdentifier(argName)) {
      argName = '$' + firstArgIndex;
    }
    return [argName];
  };

  Alt.prototype.toArgumentNameList = function (firstArgIndex, noDupCheck) {
    // `termArgNameLists` is an array of arrays where each row is the
    // argument name list that corresponds to a term in this alternation.
    const termArgNameLists = this.terms.map(term =>
      term.toArgumentNameList(firstArgIndex, true)
    );

    const argumentNameList = [];
    const numArgs = termArgNameLists[0].length;
    for (let colIdx = 0; colIdx < numArgs; colIdx++) {
      const col = [];
      for (let rowIdx = 0; rowIdx < this.terms.length; rowIdx++) {
        col.push(termArgNameLists[rowIdx][colIdx]);
      }
      const uniqueNames = copyWithoutDuplicates(col);
      argumentNameList.push(uniqueNames.join('_or_'));
    }

    if (!noDupCheck) {
      resolveDuplicatedNames(argumentNameList);
    }
    return argumentNameList;
  };

  Seq.prototype.toArgumentNameList = function (firstArgIndex, noDupCheck) {
    // Generate the argument name list, without worrying about duplicates.
    let argumentNameList = [];
    this.factors.forEach(factor => {
      const factorArgumentNameList = factor.toArgumentNameList(firstArgIndex, true);
      argumentNameList = argumentNameList.concat(factorArgumentNameList);

      // Shift the firstArgIndex to take this factor's argument names into account.
      firstArgIndex += factorArgumentNameList.length;
    });
    if (!noDupCheck) {
      resolveDuplicatedNames(argumentNameList);
    }
    return argumentNameList;
  };

  Iter.prototype.toArgumentNameList = function (firstArgIndex, noDupCheck) {
    const argumentNameList = this.expr
      .toArgumentNameList(firstArgIndex, noDupCheck)
      .map(exprArgumentString =>
        exprArgumentString[exprArgumentString.length - 1] === 's'
          ? exprArgumentString + 'es'
          : exprArgumentString + 's'
      );
    if (!noDupCheck) {
      resolveDuplicatedNames(argumentNameList);
    }
    return argumentNameList;
  };

  Opt.prototype.toArgumentNameList = function (firstArgIndex, noDupCheck) {
    return this.expr.toArgumentNameList(firstArgIndex, noDupCheck).map(argName => {
      return 'opt' + argName[0].toUpperCase() + argName.slice(1);
    });
  };

  Not.prototype.toArgumentNameList = function (firstArgIndex, noDupCheck) {
    return [];
  };

  Lookahead.prototype.toArgumentNameList = Lex.prototype.toArgumentNameList =
    function (firstArgIndex, noDupCheck) {
      return this.expr.toArgumentNameList(firstArgIndex, noDupCheck);
    };

  Apply.prototype.toArgumentNameList = function (firstArgIndex, noDupCheck) {
    return [this.ruleName];
  };

  UnicodeChar.prototype.toArgumentNameList = function (firstArgIndex, noDupCheck) {
    return ['$' + firstArgIndex];
  };

  Param.prototype.toArgumentNameList = function (firstArgIndex, noDupCheck) {
    return ['param' + this.index];
  };

  // "Value pexprs" (Value, Str, Arr, Obj) are going away soon, so we don't worry about them here.

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  // Returns a string representing the PExpr, for use as a UI label, etc.
  PExpr.prototype.toDisplayString = abstract('toDisplayString');

  Alt.prototype.toDisplayString = Seq.prototype.toDisplayString = function () {
    if (this.source) {
      return this.source.trimmed().contents;
    }
    return '[' + this.constructor.name + ']';
  };

  any.toDisplayString =
    end.toDisplayString =
    Iter.prototype.toDisplayString =
    Not.prototype.toDisplayString =
    Lookahead.prototype.toDisplayString =
    Lex.prototype.toDisplayString =
    Terminal.prototype.toDisplayString =
    Range.prototype.toDisplayString =
    Param.prototype.toDisplayString =
      function () {
        return this.toString();
      };

  Apply.prototype.toDisplayString = function () {
    if (this.args.length > 0) {
      const ps = this.args.map(arg => arg.toDisplayString());
      return this.ruleName + '<' + ps.join(',') + '>';
    } else {
      return this.ruleName;
    }
  };

  UnicodeChar.prototype.toDisplayString = function () {
    return 'Unicode [' + this.categoryOrProp + '] character';
  };

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  /*
    `Failure`s represent expressions that weren't matched while parsing. They are used to generate
    error messages automatically. The interface of `Failure`s includes the collowing methods:

    - getText() : String
    - getType() : String  (one of {"description", "string", "code"})
    - isDescription() : bool
    - isStringTerminal() : bool
    - isCode() : bool
    - isFluffy() : bool
    - makeFluffy() : void
    - subsumes(Failure) : bool
  */

  function isValidType(type) {
    return type === 'description' || type === 'string' || type === 'code';
  }

  class Failure {
    constructor(pexpr, text, type) {
      if (!isValidType(type)) {
        throw new Error('invalid Failure type: ' + type);
      }
      this.pexpr = pexpr;
      this.text = text;
      this.type = type;
      this.fluffy = false;
    }

    getPExpr() {
      return this.pexpr;
    }

    getText() {
      return this.text;
    }

    getType() {
      return this.type;
    }

    isDescription() {
      return this.type === 'description';
    }

    isStringTerminal() {
      return this.type === 'string';
    }

    isCode() {
      return this.type === 'code';
    }

    isFluffy() {
      return this.fluffy;
    }

    makeFluffy() {
      this.fluffy = true;
    }

    clearFluffy() {
      this.fluffy = false;
    }

    subsumes(that) {
      return (
        this.getText() === that.getText() &&
        this.type === that.type &&
        (!this.isFluffy() || (this.isFluffy() && that.isFluffy()))
      );
    }

    toString() {
      return this.type === 'string' ? JSON.stringify(this.getText()) : this.getText();
    }

    clone() {
      const failure = new Failure(this.pexpr, this.text, this.type);
      if (this.isFluffy()) {
        failure.makeFluffy();
      }
      return failure;
    }

    toKey() {
      return this.toString() + '#' + this.type;
    }
  }

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  PExpr.prototype.toFailure = abstract('toFailure');

  any.toFailure = function (grammar) {
    return new Failure(this, 'any object', 'description');
  };

  end.toFailure = function (grammar) {
    return new Failure(this, 'end of input', 'description');
  };

  Terminal.prototype.toFailure = function (grammar) {
    return new Failure(this, this.obj, 'string');
  };

  Range.prototype.toFailure = function (grammar) {
    // TODO: come up with something better
    return new Failure(this, JSON.stringify(this.from) + '..' + JSON.stringify(this.to), 'code');
  };

  Not.prototype.toFailure = function (grammar) {
    const description =
      this.expr === any ? 'nothing' : 'not ' + this.expr.toFailure(grammar);
    return new Failure(this, description, 'description');
  };

  Lookahead.prototype.toFailure = function (grammar) {
    return this.expr.toFailure(grammar);
  };

  Apply.prototype.toFailure = function (grammar) {
    let {description} = grammar.rules[this.ruleName];
    if (!description) {
      const article = /^[aeiouAEIOU]/.test(this.ruleName) ? 'an' : 'a';
      description = article + ' ' + this.ruleName;
    }
    return new Failure(this, description, 'description');
  };

  UnicodeChar.prototype.toFailure = function (grammar) {
    return new Failure(this, 'a Unicode [' + this.categoryOrProp + '] character', 'description');
  };

  Alt.prototype.toFailure = function (grammar) {
    const fs = this.terms.map(t => t.toFailure(grammar));
    const description = '(' + fs.join(' or ') + ')';
    return new Failure(this, description, 'description');
  };

  Seq.prototype.toFailure = function (grammar) {
    const fs = this.factors.map(f => f.toFailure(grammar));
    const description = '(' + fs.join(' ') + ')';
    return new Failure(this, description, 'description');
  };

  Iter.prototype.toFailure = function (grammar) {
    const description = '(' + this.expr.toFailure(grammar) + this.operator + ')';
    return new Failure(this, description, 'description');
  };

  // --------------------------------------------------------------------
  // Operations
  // --------------------------------------------------------------------

  /*
    e1.toString() === e2.toString() ==> e1 and e2 are semantically equivalent.
    Note that this is not an iff (<==>): e.g.,
    (~"b" "a").toString() !== ("a").toString(), even though
    ~"b" "a" and "a" are interchangeable in any grammar,
    both in terms of the languages they accept and their arities.
  */
  PExpr.prototype.toString = abstract('toString');

  any.toString = function () {
    return 'any';
  };

  end.toString = function () {
    return 'end';
  };

  Terminal.prototype.toString = function () {
    return JSON.stringify(this.obj);
  };

  Range.prototype.toString = function () {
    return JSON.stringify(this.from) + '..' + JSON.stringify(this.to);
  };

  Param.prototype.toString = function () {
    return '$' + this.index;
  };

  Lex.prototype.toString = function () {
    return '#(' + this.expr.toString() + ')';
  };

  Alt.prototype.toString = function () {
    return this.terms.length === 1
      ? this.terms[0].toString()
      : '(' + this.terms.map(term => term.toString()).join(' | ') + ')';
  };

  Seq.prototype.toString = function () {
    return this.factors.length === 1
      ? this.factors[0].toString()
      : '(' + this.factors.map(factor => factor.toString()).join(' ') + ')';
  };

  Iter.prototype.toString = function () {
    return this.expr + this.operator;
  };

  Not.prototype.toString = function () {
    return '~' + this.expr;
  };

  Lookahead.prototype.toString = function () {
    return '&' + this.expr;
  };

  Apply.prototype.toString = function () {
    if (this.args.length > 0) {
      const ps = this.args.map(arg => arg.toString());
      return this.ruleName + '<' + ps.join(',') + '>';
    } else {
      return this.ruleName;
    }
  };

  UnicodeChar.prototype.toString = function () {
    return '\\p{' + this.categoryOrProp + '}';
  };

  class CaseInsensitiveTerminal extends PExpr {
    constructor(param) {
      super();
      this.obj = param;
    }

    _getString(state) {
      const terminal = state.currentApplication().args[this.obj.index];
      assert(terminal instanceof Terminal, 'expected a Terminal expression');
      return terminal.obj;
    }

    // Implementation of the PExpr API

    allowsSkippingPrecedingSpace() {
      return true;
    }

    eval(state) {
      const {inputStream} = state;
      const origPos = inputStream.pos;
      const matchStr = this._getString(state);
      if (!inputStream.matchString(matchStr, true)) {
        state.processFailure(origPos, this);
        return false;
      } else {
        state.pushBinding(new TerminalNode(matchStr.length), origPos);
        return true;
      }
    }

    getArity() {
      return 1;
    }

    substituteParams(actuals) {
      return new CaseInsensitiveTerminal(this.obj.substituteParams(actuals));
    }

    toDisplayString() {
      return this.obj.toDisplayString() + ' (case-insensitive)';
    }

    toFailure(grammar) {
      return new Failure(
        this,
        this.obj.toFailure(grammar) + ' (case-insensitive)',
        'description'
      );
    }

    _isNullable(grammar, memo) {
      return this.obj._isNullable(grammar, memo);
    }
  }

  // --------------------------------------------------------------------

  var pexprs = /*#__PURE__*/Object.freeze({
    __proto__: null,
    CaseInsensitiveTerminal: CaseInsensitiveTerminal,
    PExpr: PExpr,
    any: any,
    end: end,
    Terminal: Terminal,
    Range: Range,
    Param: Param,
    Alt: Alt,
    Extend: Extend,
    Splice: Splice,
    Seq: Seq,
    Iter: Iter,
    Star: Star,
    Plus: Plus,
    Opt: Opt,
    Not: Not,
    Lookahead: Lookahead,
    Lex: Lex,
    Apply: Apply,
    UnicodeChar: UnicodeChar
  });

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  let builtInApplySyntacticBody;

  awaitBuiltInRules(builtInRules => {
    builtInApplySyntacticBody = builtInRules.rules.applySyntactic.body;
  });

  const applySpaces = new Apply('spaces');

  class MatchState {
    constructor(matcher, startExpr, optPositionToRecordFailures) {
      this.matcher = matcher;
      this.startExpr = startExpr;

      this.grammar = matcher.grammar;
      this.input = matcher.getInput();
      this.inputStream = new InputStream(this.input);
      this.memoTable = matcher._memoTable;

      this.userData = undefined;
      this.doNotMemoize = false;

      this._bindings = [];
      this._bindingOffsets = [];
      this._applicationStack = [];
      this._posStack = [0];
      this.inLexifiedContextStack = [false];

      this.rightmostFailurePosition = -1;
      this._rightmostFailurePositionStack = [];
      this._recordedFailuresStack = [];

      if (optPositionToRecordFailures !== undefined) {
        this.positionToRecordFailures = optPositionToRecordFailures;
        this.recordedFailures = Object.create(null);
      }
    }

    posToOffset(pos) {
      return pos - this._posStack[this._posStack.length - 1];
    }

    enterApplication(posInfo, app) {
      this._posStack.push(this.inputStream.pos);
      this._applicationStack.push(app);
      this.inLexifiedContextStack.push(false);
      posInfo.enter(app);
      this._rightmostFailurePositionStack.push(this.rightmostFailurePosition);
      this.rightmostFailurePosition = -1;
    }

    exitApplication(posInfo, optNode) {
      const origPos = this._posStack.pop();
      this._applicationStack.pop();
      this.inLexifiedContextStack.pop();
      posInfo.exit();

      this.rightmostFailurePosition = Math.max(
        this.rightmostFailurePosition,
        this._rightmostFailurePositionStack.pop()
      );

      if (optNode) {
        this.pushBinding(optNode, origPos);
      }
    }

    enterLexifiedContext() {
      this.inLexifiedContextStack.push(true);
    }

    exitLexifiedContext() {
      this.inLexifiedContextStack.pop();
    }

    currentApplication() {
      return this._applicationStack[this._applicationStack.length - 1];
    }

    inSyntacticContext() {
      const currentApplication = this.currentApplication();
      if (currentApplication) {
        return currentApplication.isSyntactic() && !this.inLexifiedContext();
      } else {
        // The top-level context is syntactic if the start application is.
        return this.startExpr.factors[0].isSyntactic();
      }
    }

    inLexifiedContext() {
      return this.inLexifiedContextStack[this.inLexifiedContextStack.length - 1];
    }

    skipSpaces() {
      this.pushFailuresInfo();
      this.eval(applySpaces);
      this.popBinding();
      this.popFailuresInfo();
      return this.inputStream.pos;
    }

    skipSpacesIfInSyntacticContext() {
      return this.inSyntacticContext() ? this.skipSpaces() : this.inputStream.pos;
    }

    maybeSkipSpacesBefore(expr) {
      if (expr.allowsSkippingPrecedingSpace() && expr !== applySpaces) {
        return this.skipSpacesIfInSyntacticContext();
      } else {
        return this.inputStream.pos;
      }
    }

    pushBinding(node, origPos) {
      this._bindings.push(node);
      this._bindingOffsets.push(this.posToOffset(origPos));
    }

    popBinding() {
      this._bindings.pop();
      this._bindingOffsets.pop();
    }

    numBindings() {
      return this._bindings.length;
    }

    truncateBindings(newLength) {
      // Yes, this is this really faster than setting the `length` property (tested with
      // bin/es5bench on Node v6.1.0).
      // Update 2021-10-25: still true on v14.15.5 — it's ~20% speedup on es5bench.
      while (this._bindings.length > newLength) {
        this.popBinding();
      }
    }

    getCurrentPosInfo() {
      return this.getPosInfo(this.inputStream.pos);
    }

    getPosInfo(pos) {
      let posInfo = this.memoTable[pos];
      if (!posInfo) {
        posInfo = this.memoTable[pos] = new PosInfo();
      }
      return posInfo;
    }

    processFailure(pos, expr) {
      this.rightmostFailurePosition = Math.max(this.rightmostFailurePosition, pos);

      if (this.recordedFailures && pos === this.positionToRecordFailures) {
        const app = this.currentApplication();
        if (app) {
          // Substitute parameters with the actual pexprs that were passed to
          // the current rule.
          expr = expr.substituteParams(app.args);
        }

        this.recordFailure(expr.toFailure(this.grammar), false);
      }
    }

    recordFailure(failure, shouldCloneIfNew) {
      const key = failure.toKey();
      if (!this.recordedFailures[key]) {
        this.recordedFailures[key] = shouldCloneIfNew ? failure.clone() : failure;
      } else if (this.recordedFailures[key].isFluffy() && !failure.isFluffy()) {
        this.recordedFailures[key].clearFluffy();
      }
    }

    recordFailures(failures, shouldCloneIfNew) {
      Object.keys(failures).forEach(key => {
        this.recordFailure(failures[key], shouldCloneIfNew);
      });
    }

    cloneRecordedFailures() {
      if (!this.recordedFailures) {
        return undefined;
      }

      const ans = Object.create(null);
      Object.keys(this.recordedFailures).forEach(key => {
        ans[key] = this.recordedFailures[key].clone();
      });
      return ans;
    }

    getRightmostFailurePosition() {
      return this.rightmostFailurePosition;
    }

    _getRightmostFailureOffset() {
      return this.rightmostFailurePosition >= 0
        ? this.posToOffset(this.rightmostFailurePosition)
        : -1;
    }

    // Returns the memoized trace entry for `expr` at `pos`, if one exists, `null` otherwise.
    getMemoizedTraceEntry(pos, expr) {
      const posInfo = this.memoTable[pos];
      if (posInfo && expr instanceof Apply) {
        const memoRec = posInfo.memo[expr.toMemoKey()];
        if (memoRec && memoRec.traceEntry) {
          const entry = memoRec.traceEntry.cloneWithExpr(expr);
          entry.isMemoized = true;
          return entry;
        }
      }
      return null;
    }

    // Returns a new trace entry, with the currently active trace array as its children.
    getTraceEntry(pos, expr, succeeded, bindings) {
      if (expr instanceof Apply) {
        const app = this.currentApplication();
        const actuals = app ? app.args : [];
        expr = expr.substituteParams(actuals);
      }
      return (
        this.getMemoizedTraceEntry(pos, expr) ||
        new Trace(this.input, pos, this.inputStream.pos, expr, succeeded, bindings, this.trace)
      );
    }

    isTracing() {
      return !!this.trace;
    }

    hasNecessaryInfo(memoRec) {
      if (this.trace && !memoRec.traceEntry) {
        return false;
      }

      if (
        this.recordedFailures &&
        this.inputStream.pos + memoRec.rightmostFailureOffset === this.positionToRecordFailures
      ) {
        return !!memoRec.failuresAtRightmostPosition;
      }

      return true;
    }

    useMemoizedResult(origPos, memoRec) {
      if (this.trace) {
        this.trace.push(memoRec.traceEntry);
      }

      const memoRecRightmostFailurePosition =
        this.inputStream.pos + memoRec.rightmostFailureOffset;
      this.rightmostFailurePosition = Math.max(
        this.rightmostFailurePosition,
        memoRecRightmostFailurePosition
      );
      if (
        this.recordedFailures &&
        this.positionToRecordFailures === memoRecRightmostFailurePosition &&
        memoRec.failuresAtRightmostPosition
      ) {
        this.recordFailures(memoRec.failuresAtRightmostPosition, true);
      }

      this.inputStream.examinedLength = Math.max(
        this.inputStream.examinedLength,
        memoRec.examinedLength + origPos
      );

      if (memoRec.value) {
        this.inputStream.pos += memoRec.matchLength;
        this.pushBinding(memoRec.value, origPos);
        return true;
      }
      return false;
    }

    // Evaluate `expr` and return `true` if it succeeded, `false` otherwise. On success, `bindings`
    // will have `expr.getArity()` more elements than before, and the input stream's position may
    // have increased. On failure, `bindings` and position will be unchanged.
    eval(expr) {
      const {inputStream} = this;
      const origNumBindings = this._bindings.length;
      const origUserData = this.userData;

      let origRecordedFailures;
      if (this.recordedFailures) {
        origRecordedFailures = this.recordedFailures;
        this.recordedFailures = Object.create(null);
      }

      const origPos = inputStream.pos;
      const memoPos = this.maybeSkipSpacesBefore(expr);

      let origTrace;
      if (this.trace) {
        origTrace = this.trace;
        this.trace = [];
      }

      // Do the actual evaluation.
      const ans = expr.eval(this);

      if (this.trace) {
        const bindings = this._bindings.slice(origNumBindings);
        const traceEntry = this.getTraceEntry(memoPos, expr, ans, bindings);
        traceEntry.isImplicitSpaces = expr === applySpaces;
        traceEntry.isRootNode = expr === this.startExpr;
        origTrace.push(traceEntry);
        this.trace = origTrace;
      }

      if (ans) {
        if (this.recordedFailures && inputStream.pos === this.positionToRecordFailures) {
          Object.keys(this.recordedFailures).forEach(key => {
            this.recordedFailures[key].makeFluffy();
          });
        }
      } else {
        // Reset the position, bindings, and userData.
        inputStream.pos = origPos;
        this.truncateBindings(origNumBindings);
        this.userData = origUserData;
      }

      if (this.recordedFailures) {
        this.recordFailures(origRecordedFailures, false);
      }

      // The built-in applySyntactic rule needs special handling: we want to skip
      // trailing spaces, just as with the top-level application of a syntactic rule.
      if (expr === builtInApplySyntacticBody) {
        this.skipSpaces();
      }

      return ans;
    }

    getMatchResult() {
      this.grammar._setUpMatchState(this);
      this.eval(this.startExpr);
      let rightmostFailures;
      if (this.recordedFailures) {
        rightmostFailures = Object.keys(this.recordedFailures).map(
          key => this.recordedFailures[key]
        );
      }
      const cst = this._bindings[0];
      if (cst) {
        cst.grammar = this.grammar;
      }
      return new MatchResult(
        this.matcher,
        this.input,
        this.startExpr,
        cst,
        this._bindingOffsets[0],
        this.rightmostFailurePosition,
        rightmostFailures
      );
    }

    getTrace() {
      this.trace = [];
      const matchResult = this.getMatchResult();

      // The trace node for the start rule is always the last entry. If it is a syntactic rule,
      // the first entry is for an application of 'spaces'.
      // TODO(pdubroy): Clean this up by introducing a special `Match<startAppl>` rule, which will
      // ensure that there is always a single root trace node.
      const rootTrace = this.trace[this.trace.length - 1];
      rootTrace.result = matchResult;
      return rootTrace;
    }

    pushFailuresInfo() {
      this._rightmostFailurePositionStack.push(this.rightmostFailurePosition);
      this._recordedFailuresStack.push(this.recordedFailures);
    }

    popFailuresInfo() {
      this.rightmostFailurePosition = this._rightmostFailurePositionStack.pop();
      this.recordedFailures = this._recordedFailuresStack.pop();
    }
  }

  class Matcher {
    constructor(grammar) {
      this.grammar = grammar;
      this._memoTable = [];
      this._input = '';
      this._isMemoTableStale = false;
    }

    _resetMemoTable() {
      this._memoTable = [];
      this._isMemoTableStale = false;
    }

    getInput() {
      return this._input;
    }

    setInput(str) {
      if (this._input !== str) {
        this.replaceInputRange(0, this._input.length, str);
      }
      return this;
    }

    replaceInputRange(startIdx, endIdx, str) {
      const prevInput = this._input;
      const memoTable = this._memoTable;
      if (
        startIdx < 0 ||
        startIdx > prevInput.length ||
        endIdx < 0 ||
        endIdx > prevInput.length ||
        startIdx > endIdx
      ) {
        throw new Error('Invalid indices: ' + startIdx + ' and ' + endIdx);
      }

      // update input
      this._input = prevInput.slice(0, startIdx) + str + prevInput.slice(endIdx);
      if (this._input !== prevInput && memoTable.length > 0) {
        this._isMemoTableStale = true;
      }

      // update memo table (similar to the above)
      const restOfMemoTable = memoTable.slice(endIdx);
      memoTable.length = startIdx;
      for (let idx = 0; idx < str.length; idx++) {
        memoTable.push(undefined);
      }
      for (const posInfo of restOfMemoTable) {
        memoTable.push(posInfo);
      }

      // Invalidate memoRecs
      for (let pos = 0; pos < startIdx; pos++) {
        const posInfo = memoTable[pos];
        if (posInfo) {
          posInfo.clearObsoleteEntries(pos, startIdx);
        }
      }

      return this;
    }

    match(optStartApplicationStr, options = {incremental: true}) {
      return this._match(this._getStartExpr(optStartApplicationStr), {
        incremental: options.incremental,
        tracing: false,
      });
    }

    trace(optStartApplicationStr, options = {incremental: true}) {
      return this._match(this._getStartExpr(optStartApplicationStr), {
        incremental: options.incremental,
        tracing: true,
      });
    }

    _match(startExpr, options = {}) {
      const opts = {
        tracing: false,
        incremental: true,
        positionToRecordFailures: undefined,
        ...options,
      };
      if (!opts.incremental) {
        this._resetMemoTable();
      } else if (this._isMemoTableStale && !this.grammar.supportsIncrementalParsing) {
        throw grammarDoesNotSupportIncrementalParsing(this.grammar);
      }

      const state = new MatchState(this, startExpr, opts.positionToRecordFailures);
      return opts.tracing ? state.getTrace() : state.getMatchResult();
    }

    /*
      Returns the starting expression for this Matcher's associated grammar. If
      `optStartApplicationStr` is specified, it is a string expressing a rule application in the
      grammar. If not specified, the grammar's default start rule will be used.
    */
    _getStartExpr(optStartApplicationStr) {
      const applicationStr = optStartApplicationStr || this.grammar.defaultStartRule;
      if (!applicationStr) {
        throw new Error('Missing start rule argument -- the grammar has no default start rule.');
      }

      const startApp = this.grammar.parseApplication(applicationStr);
      return new Seq([startApp, end]);
    }
  }

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  const globalActionStack = [];

  const hasOwnProperty = (x, prop) => Object.prototype.hasOwnProperty.call(x, prop);

  // ----------------- Wrappers -----------------

  // Wrappers decorate CST nodes with all of the functionality (i.e., operations and attributes)
  // provided by a Semantics (see below). `Wrapper` is the abstract superclass of all wrappers. A
  // `Wrapper` must have `_node` and `_semantics` instance variables, which refer to the CST node and
  // Semantics (resp.) for which it was created, and a `_childWrappers` instance variable which is
  // used to cache the wrapper instances that are created for its child nodes. Setting these instance
  // variables is the responsibility of the constructor of each Semantics-specific subclass of
  // `Wrapper`.
  class Wrapper {
    constructor(node, sourceInterval, baseInterval) {
      this._node = node;
      this.source = sourceInterval;

      // The interval that the childOffsets of `node` are relative to. It should be the source
      // of the closest Nonterminal node.
      this._baseInterval = baseInterval;

      if (node.isNonterminal()) {
        assert(sourceInterval === baseInterval);
      }
      this._childWrappers = [];
    }

    _forgetMemoizedResultFor(attributeName) {
      // Remove the memoized attribute from the cstNode and all its children.
      delete this._node[this._semantics.attributeKeys[attributeName]];
      this.children.forEach(child => {
        child._forgetMemoizedResultFor(attributeName);
      });
    }

    // Returns the wrapper of the specified child node. Child wrappers are created lazily and
    // cached in the parent wrapper's `_childWrappers` instance variable.
    child(idx) {
      if (!(0 <= idx && idx < this._node.numChildren())) {
        // TODO: Consider throwing an exception here.
        return undefined;
      }
      let childWrapper = this._childWrappers[idx];
      if (!childWrapper) {
        const childNode = this._node.childAt(idx);
        const offset = this._node.childOffsets[idx];

        const source = this._baseInterval.subInterval(offset, childNode.matchLength);
        const base = childNode.isNonterminal() ? source : this._baseInterval;
        childWrapper = this._childWrappers[idx] = this._semantics.wrap(childNode, source, base);
      }
      return childWrapper;
    }

    // Returns an array containing the wrappers of all of the children of the node associated
    // with this wrapper.
    _children() {
      // Force the creation of all child wrappers
      for (let idx = 0; idx < this._node.numChildren(); idx++) {
        this.child(idx);
      }
      return this._childWrappers;
    }

    // Returns `true` if the CST node associated with this wrapper corresponds to an iteration
    // expression, i.e., a Kleene-*, Kleene-+, or an optional. Returns `false` otherwise.
    isIteration() {
      return this._node.isIteration();
    }

    // Returns `true` if the CST node associated with this wrapper is a terminal node, `false`
    // otherwise.
    isTerminal() {
      return this._node.isTerminal();
    }

    // Returns `true` if the CST node associated with this wrapper is a nonterminal node, `false`
    // otherwise.
    isNonterminal() {
      return this._node.isNonterminal();
    }

    // Returns `true` if the CST node associated with this wrapper is a nonterminal node
    // corresponding to a syntactic rule, `false` otherwise.
    isSyntactic() {
      return this.isNonterminal() && this._node.isSyntactic();
    }

    // Returns `true` if the CST node associated with this wrapper is a nonterminal node
    // corresponding to a lexical rule, `false` otherwise.
    isLexical() {
      return this.isNonterminal() && this._node.isLexical();
    }

    // Returns `true` if the CST node associated with this wrapper is an iterator node
    // having either one or no child (? operator), `false` otherwise.
    // Otherwise, throws an exception.
    isOptional() {
      return this._node.isOptional();
    }

    // Create a new _iter wrapper in the same semantics as this wrapper.
    iteration(optChildWrappers) {
      const childWrappers = optChildWrappers || [];

      const childNodes = childWrappers.map(c => c._node);
      const iter = new IterationNode(childNodes, [], -1, false);

      const wrapper = this._semantics.wrap(iter, null, null);
      wrapper._childWrappers = childWrappers;
      return wrapper;
    }

    // Returns an array containing the children of this CST node.
    get children() {
      return this._children();
    }

    // Returns the name of grammar rule that created this CST node.
    get ctorName() {
      return this._node.ctorName;
    }

    // Returns the number of children of this CST node.
    get numChildren() {
      return this._node.numChildren();
    }

    // Returns the contents of the input stream consumed by this CST node.
    get sourceString() {
      return this.source.contents;
    }
  }

  // ----------------- Semantics -----------------

  // A Semantics is a container for a family of Operations and Attributes for a given grammar.
  // Semantics enable modularity (different clients of a grammar can create their set of operations
  // and attributes in isolation) and extensibility even when operations and attributes are mutually-
  // recursive. This constructor should not be called directly except from
  // `Semantics.createSemantics`. The normal ways to create a Semantics, given a grammar 'g', are
  // `g.createSemantics()` and `g.extendSemantics(parentSemantics)`.
  class Semantics {
    constructor(grammar, superSemantics) {
      const self = this;
      this.grammar = grammar;
      this.checkedActionDicts = false;

      // Constructor for wrapper instances, which are passed as the arguments to the semantic actions
      // of an operation or attribute. Operations and attributes require double dispatch: the semantic
      // action is chosen based on both the node's type and the semantics. Wrappers ensure that
      // the `execute` method is called with the correct (most specific) semantics object as an
      // argument.
      this.Wrapper = class extends (superSemantics ? superSemantics.Wrapper : Wrapper) {
        constructor(node, sourceInterval, baseInterval) {
          super(node, sourceInterval, baseInterval);
          self.checkActionDictsIfHaventAlready();
          this._semantics = self;
        }

        toString() {
          return '[semantics wrapper for ' + self.grammar.name + ']';
        }
      };

      this.super = superSemantics;
      if (superSemantics) {
        if (!(grammar.equals(this.super.grammar) || grammar._inheritsFrom(this.super.grammar))) {
          throw new Error(
            "Cannot extend a semantics for grammar '" +
              this.super.grammar.name +
              "' for use with grammar '" +
              grammar.name +
              "' (not a sub-grammar)"
          );
        }
        this.operations = Object.create(this.super.operations);
        this.attributes = Object.create(this.super.attributes);
        this.attributeKeys = Object.create(null);

        // Assign unique symbols for each of the attributes inherited from the super-semantics so that
        // they are memoized independently.

        for (const attributeName in this.attributes) {
          Object.defineProperty(this.attributeKeys, attributeName, {
            value: uniqueId(attributeName),
          });
        }
      } else {
        this.operations = Object.create(null);
        this.attributes = Object.create(null);
        this.attributeKeys = Object.create(null);
      }
    }

    toString() {
      return '[semantics for ' + this.grammar.name + ']';
    }

    checkActionDictsIfHaventAlready() {
      if (!this.checkedActionDicts) {
        this.checkActionDicts();
        this.checkedActionDicts = true;
      }
    }

    // Checks that the action dictionaries for all operations and attributes in this semantics,
    // including the ones that were inherited from the super-semantics, agree with the grammar.
    // Throws an exception if one or more of them doesn't.
    checkActionDicts() {
      let name;

      for (name in this.operations) {
        this.operations[name].checkActionDict(this.grammar);
      }

      for (name in this.attributes) {
        this.attributes[name].checkActionDict(this.grammar);
      }
    }

    toRecipe(semanticsOnly) {
      function hasSuperSemantics(s) {
        return s.super !== Semantics.BuiltInSemantics._getSemantics();
      }

      let str = '(function(g) {\n';
      if (hasSuperSemantics(this)) {
        str += '  var semantics = ' + this.super.toRecipe(true) + '(g';

        const superSemanticsGrammar = this.super.grammar;
        let relatedGrammar = this.grammar;
        while (relatedGrammar !== superSemanticsGrammar) {
          str += '.superGrammar';
          relatedGrammar = relatedGrammar.superGrammar;
        }

        str += ');\n';
        str += '  return g.extendSemantics(semantics)';
      } else {
        str += '  return g.createSemantics()';
      }
      ['Operation', 'Attribute'].forEach(type => {
        const semanticOperations = this[type.toLowerCase() + 's'];
        Object.keys(semanticOperations).forEach(name => {
          const {actionDict, formals, builtInDefault} = semanticOperations[name];

          let signature = name;
          if (formals.length > 0) {
            signature += '(' + formals.join(', ') + ')';
          }

          let method;
          if (hasSuperSemantics(this) && this.super[type.toLowerCase() + 's'][name]) {
            method = 'extend' + type;
          } else {
            method = 'add' + type;
          }
          str += '\n    .' + method + '(' + JSON.stringify(signature) + ', {';

          const srcArray = [];
          Object.keys(actionDict).forEach(actionName => {
            if (actionDict[actionName] !== builtInDefault) {
              let source = actionDict[actionName].toString().trim();

              // Convert method shorthand to plain old function syntax.
              // https://github.com/ohmjs/ohm/issues/263
              source = source.replace(/^.*\(/, 'function(');

              srcArray.push('\n      ' + JSON.stringify(actionName) + ': ' + source);
            }
          });
          str += srcArray.join(',') + '\n    })';
        });
      });
      str += ';\n  })';

      if (!semanticsOnly) {
        str =
          '(function() {\n' +
          '  var grammar = this.fromRecipe(' +
          this.grammar.toRecipe() +
          ');\n' +
          '  var semantics = ' +
          str +
          '(grammar);\n' +
          '  return semantics;\n' +
          '});\n';
      }

      return str;
    }

    addOperationOrAttribute(type, signature, actionDict) {
      const typePlural = type + 's';

      const parsedNameAndFormalArgs = parseSignature(signature, type);
      const {name} = parsedNameAndFormalArgs;
      const {formals} = parsedNameAndFormalArgs;

      // TODO: check that there are no duplicate formal arguments

      this.assertNewName(name, type);

      // Create the action dictionary for this operation / attribute that contains a `_default` action
      // which defines the default behavior of iteration, terminal, and non-terminal nodes...
      const builtInDefault = newDefaultAction(type, name, doIt);
      const realActionDict = {_default: builtInDefault};
      // ... and add in the actions supplied by the programmer, which may override some or all of the
      // default ones.
      Object.keys(actionDict).forEach(name => {
        realActionDict[name] = actionDict[name];
      });

      const entry =
        type === 'operation'
          ? new Operation(name, formals, realActionDict, builtInDefault)
          : new Attribute(name, realActionDict, builtInDefault);

      // The following check is not strictly necessary (it will happen later anyway) but it's better
      // to catch errors early.
      entry.checkActionDict(this.grammar);

      this[typePlural][name] = entry;

      function doIt(...args) {
        // Dispatch to most specific version of this operation / attribute -- it may have been
        // overridden by a sub-semantics.
        const thisThing = this._semantics[typePlural][name];

        // Check that the caller passed the correct number of arguments.
        if (arguments.length !== thisThing.formals.length) {
          throw new Error(
            'Invalid number of arguments passed to ' +
              name +
              ' ' +
              type +
              ' (expected ' +
              thisThing.formals.length +
              ', got ' +
              arguments.length +
              ')'
          );
        }

        // Create an "arguments object" from the arguments that were passed to this
        // operation / attribute.
        const argsObj = Object.create(null);
        for (const [idx, val] of Object.entries(args)) {
          const formal = thisThing.formals[idx];
          argsObj[formal] = val;
        }

        const oldArgs = this.args;
        this.args = argsObj;
        const ans = thisThing.execute(this._semantics, this);
        this.args = oldArgs;
        return ans;
      }

      if (type === 'operation') {
        this.Wrapper.prototype[name] = doIt;
        this.Wrapper.prototype[name].toString = function () {
          return '[' + name + ' operation]';
        };
      } else {
        Object.defineProperty(this.Wrapper.prototype, name, {
          get: doIt,
          configurable: true, // So the property can be deleted.
        });
        Object.defineProperty(this.attributeKeys, name, {
          value: uniqueId(name),
        });
      }
    }

    extendOperationOrAttribute(type, name, actionDict) {
      const typePlural = type + 's';

      // Make sure that `name` really is just a name, i.e., that it doesn't also contain formals.
      parseSignature(name, 'attribute');

      if (!(this.super && name in this.super[typePlural])) {
        throw new Error(
          'Cannot extend ' +
            type +
            " '" +
            name +
            "': did not inherit an " +
            type +
            ' with that name'
        );
      }
      if (hasOwnProperty(this[typePlural], name)) {
        throw new Error('Cannot extend ' + type + " '" + name + "' again");
      }

      // Create a new operation / attribute whose actionDict delegates to the super operation /
      // attribute's actionDict, and which has all the keys from `inheritedActionDict`.
      const inheritedFormals = this[typePlural][name].formals;
      const inheritedActionDict = this[typePlural][name].actionDict;
      const newActionDict = Object.create(inheritedActionDict);
      Object.keys(actionDict).forEach(name => {
        newActionDict[name] = actionDict[name];
      });

      this[typePlural][name] =
        type === 'operation'
          ? new Operation(name, inheritedFormals, newActionDict)
          : new Attribute(name, newActionDict);

      // The following check is not strictly necessary (it will happen later anyway) but it's better
      // to catch errors early.
      this[typePlural][name].checkActionDict(this.grammar);
    }

    assertNewName(name, type) {
      if (hasOwnProperty(Wrapper.prototype, name)) {
        throw new Error('Cannot add ' + type + " '" + name + "': that's a reserved name");
      }
      if (name in this.operations) {
        throw new Error(
          'Cannot add ' + type + " '" + name + "': an operation with that name already exists"
        );
      }
      if (name in this.attributes) {
        throw new Error(
          'Cannot add ' + type + " '" + name + "': an attribute with that name already exists"
        );
      }
    }

    // Returns a wrapper for the given CST `node` in this semantics.
    // If `node` is already a wrapper, returns `node` itself.  // TODO: why is this needed?
    wrap(node, source, optBaseInterval) {
      const baseInterval = optBaseInterval || source;
      return node instanceof this.Wrapper ? node : new this.Wrapper(node, source, baseInterval);
    }
  }

  function parseSignature(signature, type) {
    if (!Semantics.prototypeGrammar) {
      // The Operations and Attributes grammar won't be available while Ohm is loading,
      // but we can get away the following simplification b/c none of the operations
      // that are used while loading take arguments.
      assert(signature.indexOf('(') === -1);
      return {
        name: signature,
        formals: [],
      };
    }

    const r = Semantics.prototypeGrammar.match(
      signature,
      type === 'operation' ? 'OperationSignature' : 'AttributeSignature'
    );
    if (r.failed()) {
      throw new Error(r.message);
    }

    return Semantics.prototypeGrammarSemantics(r).parse();
  }

  function newDefaultAction(type, name, doIt) {
    return function (...children) {
      const thisThing = this._semantics.operations[name] || this._semantics.attributes[name];
      const args = thisThing.formals.map(formal => this.args[formal]);

      if (!this.isIteration() && children.length === 1) {
        // This CST node corresponds to a non-terminal in the grammar (e.g., AddExpr). The fact that
        // we got here means that this action dictionary doesn't have an action for this particular
        // non-terminal or a generic `_nonterminal` action.
        // As a convenience, if this node only has one child, we just return the result of applying
        // this operation / attribute to the child node.
        return doIt.apply(children[0], args);
      } else {
        // Otherwise, we throw an exception to let the programmer know that we don't know what
        // to do with this node.
        throw missingSemanticAction(this.ctorName, name, type, globalActionStack);
      }
    };
  }

  // Creates a new Semantics instance for `grammar`, inheriting operations and attributes from
  // `optSuperSemantics`, if it is specified. Returns a function that acts as a proxy for the new
  // Semantics instance. When that function is invoked with a CST node as an argument, it returns
  // a wrapper for that node which gives access to the operations and attributes provided by this
  // semantics.
  Semantics.createSemantics = function (grammar, optSuperSemantics) {
    const s = new Semantics(
      grammar,
      optSuperSemantics !== undefined
        ? optSuperSemantics
        : Semantics.BuiltInSemantics._getSemantics()
    );

    // To enable clients to invoke a semantics like a function, return a function that acts as a proxy
    // for `s`, which is the real `Semantics` instance.
    const proxy = function ASemantics(matchResult) {
      if (!(matchResult instanceof MatchResult)) {
        throw new TypeError(
          'Semantics expected a MatchResult, but got ' +
            unexpectedObjToString(matchResult)
        );
      }
      if (matchResult.failed()) {
        throw new TypeError('cannot apply Semantics to ' + matchResult.toString());
      }

      const cst = matchResult._cst;
      if (cst.grammar !== grammar) {
        throw new Error(
          "Cannot use a MatchResult from grammar '" +
            cst.grammar.name +
            "' with a semantics for '" +
            grammar.name +
            "'"
        );
      }
      const inputStream = new InputStream(matchResult.input);
      return s.wrap(cst, inputStream.interval(matchResult._cstOffset, matchResult.input.length));
    };

    // Forward public methods from the proxy to the semantics instance.
    proxy.addOperation = function (signature, actionDict) {
      s.addOperationOrAttribute('operation', signature, actionDict);
      return proxy;
    };
    proxy.extendOperation = function (name, actionDict) {
      s.extendOperationOrAttribute('operation', name, actionDict);
      return proxy;
    };
    proxy.addAttribute = function (name, actionDict) {
      s.addOperationOrAttribute('attribute', name, actionDict);
      return proxy;
    };
    proxy.extendAttribute = function (name, actionDict) {
      s.extendOperationOrAttribute('attribute', name, actionDict);
      return proxy;
    };
    proxy._getActionDict = function (operationOrAttributeName) {
      const action =
        s.operations[operationOrAttributeName] || s.attributes[operationOrAttributeName];
      if (!action) {
        throw new Error(
          '"' +
            operationOrAttributeName +
            '" is not a valid operation or attribute ' +
            'name in this semantics for "' +
            grammar.name +
            '"'
        );
      }
      return action.actionDict;
    };
    proxy._remove = function (operationOrAttributeName) {
      let semantic;
      if (operationOrAttributeName in s.operations) {
        semantic = s.operations[operationOrAttributeName];
        delete s.operations[operationOrAttributeName];
      } else if (operationOrAttributeName in s.attributes) {
        semantic = s.attributes[operationOrAttributeName];
        delete s.attributes[operationOrAttributeName];
      }
      delete s.Wrapper.prototype[operationOrAttributeName];
      return semantic;
    };
    proxy.getOperationNames = function () {
      return Object.keys(s.operations);
    };
    proxy.getAttributeNames = function () {
      return Object.keys(s.attributes);
    };
    proxy.getGrammar = function () {
      return s.grammar;
    };
    proxy.toRecipe = function (semanticsOnly) {
      return s.toRecipe(semanticsOnly);
    };

    // Make the proxy's toString() work.
    proxy.toString = s.toString.bind(s);

    // Returns the semantics for the proxy.
    proxy._getSemantics = function () {
      return s;
    };

    return proxy;
  };

  // ----------------- Operation -----------------

  // An Operation represents a function to be applied to a concrete syntax tree (CST) -- it's very
  // similar to a Visitor (http://en.wikipedia.org/wiki/Visitor_pattern). An operation is executed by
  // recursively walking the CST, and at each node, invoking the matching semantic action from
  // `actionDict`. See `Operation.prototype.execute` for details of how a CST node's matching semantic
  // action is found.
  class Operation {
    constructor(name, formals, actionDict, builtInDefault) {
      this.name = name;
      this.formals = formals;
      this.actionDict = actionDict;
      this.builtInDefault = builtInDefault;
    }

    checkActionDict(grammar) {
      grammar._checkTopDownActionDict(this.typeName, this.name, this.actionDict);
    }

    // Execute this operation on the CST node associated with `nodeWrapper` in the context of the
    // given Semantics instance.
    execute(semantics, nodeWrapper) {
      try {
        // Look for a semantic action whose name matches the node's constructor name, which is either
        // the name of a rule in the grammar, or '_terminal' (for a terminal node), or '_iter' (for an
        // iteration node).
        const {ctorName} = nodeWrapper._node;
        let actionFn = this.actionDict[ctorName];
        if (actionFn) {
          globalActionStack.push([this, ctorName]);
          return actionFn.apply(nodeWrapper, nodeWrapper._children());
        }

        // The action dictionary does not contain a semantic action for this specific type of node.
        // If this is a nonterminal node and the programmer has provided a `_nonterminal` semantic
        // action, we invoke it:
        if (nodeWrapper.isNonterminal()) {
          actionFn = this.actionDict._nonterminal;
          if (actionFn) {
            globalActionStack.push([this, '_nonterminal', ctorName]);
            return actionFn.apply(nodeWrapper, nodeWrapper._children());
          }
        }

        // Otherwise, we invoke the '_default' semantic action.
        globalActionStack.push([this, 'default action', ctorName]);
        return this.actionDict._default.apply(nodeWrapper, nodeWrapper._children());
      } finally {
        globalActionStack.pop();
      }
    }
  }

  Operation.prototype.typeName = 'operation';

  // ----------------- Attribute -----------------

  // Attributes are Operations whose results are memoized. This means that, for any given semantics,
  // the semantic action for a CST node will be invoked no more than once.
  class Attribute extends Operation {
    constructor(name, actionDict, builtInDefault) {
      super(name, [], actionDict, builtInDefault);
    }

    execute(semantics, nodeWrapper) {
      const node = nodeWrapper._node;
      const key = semantics.attributeKeys[this.name];
      if (!hasOwnProperty(node, key)) {
        // The following is a super-send -- isn't JS beautiful? :/
        node[key] = Operation.prototype.execute.call(this, semantics, nodeWrapper);
      }
      return node[key];
    }
  }

  Attribute.prototype.typeName = 'attribute';

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  const SPECIAL_ACTION_NAMES = ['_iter', '_terminal', '_nonterminal', '_default'];

  function getSortedRuleValues(grammar) {
    return Object.keys(grammar.rules)
      .sort()
      .map(name => grammar.rules[name]);
  }

  // Until ES2019, JSON was not a valid subset of JavaScript because U+2028 (line separator)
  // and U+2029 (paragraph separator) are allowed in JSON string literals, but not in JS.
  // This function properly encodes those two characters so that the resulting string is
  // represents both valid JSON, and valid JavaScript (for ES2018 and below).
  // See https://v8.dev/features/subsume-json for more details.
  const jsonToJS = str => str.replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');

  let ohmGrammar$1;
  let buildGrammar$1;

  class Grammar {
    constructor(name, superGrammar, rules, optDefaultStartRule) {
      this.name = name;
      this.superGrammar = superGrammar;
      this.rules = rules;
      if (optDefaultStartRule) {
        if (!(optDefaultStartRule in rules)) {
          throw new Error(
            "Invalid start rule: '" +
              optDefaultStartRule +
              "' is not a rule in grammar '" +
              name +
              "'"
          );
        }
        this.defaultStartRule = optDefaultStartRule;
      }
      this._matchStateInitializer = undefined;
      this.supportsIncrementalParsing = true;
    }

    matcher() {
      return new Matcher(this);
    }

    // Return true if the grammar is a built-in grammar, otherwise false.
    // NOTE: This might give an unexpected result if called before BuiltInRules is defined!
    isBuiltIn() {
      return this === Grammar.ProtoBuiltInRules || this === Grammar.BuiltInRules;
    }

    equals(g) {
      if (this === g) {
        return true;
      }
      // Do the cheapest comparisons first.
      if (
        g == null ||
        this.name !== g.name ||
        this.defaultStartRule !== g.defaultStartRule ||
        !(this.superGrammar === g.superGrammar || this.superGrammar.equals(g.superGrammar))
      ) {
        return false;
      }
      const myRules = getSortedRuleValues(this);
      const otherRules = getSortedRuleValues(g);
      return (
        myRules.length === otherRules.length &&
        myRules.every((rule, i) => {
          return (
            rule.description === otherRules[i].description &&
            rule.formals.join(',') === otherRules[i].formals.join(',') &&
            rule.body.toString() === otherRules[i].body.toString()
          );
        })
      );
    }

    match(input, optStartApplication) {
      const m = this.matcher();
      m.replaceInputRange(0, 0, input);
      return m.match(optStartApplication);
    }

    trace(input, optStartApplication) {
      const m = this.matcher();
      m.replaceInputRange(0, 0, input);
      return m.trace(optStartApplication);
    }

    createSemantics() {
      return Semantics.createSemantics(this);
    }

    extendSemantics(superSemantics) {
      return Semantics.createSemantics(this, superSemantics._getSemantics());
    }

    // Check that every key in `actionDict` corresponds to a semantic action, and that it maps to
    // a function of the correct arity. If not, throw an exception.
    _checkTopDownActionDict(what, name, actionDict) {
      const problems = [];

      for (const k in actionDict) {
        const v = actionDict[k];
        const isSpecialAction = SPECIAL_ACTION_NAMES.includes(k);

        if (!isSpecialAction && !(k in this.rules)) {
          problems.push(`'${k}' is not a valid semantic action for '${this.name}'`);
          continue;
        }
        if (typeof v !== 'function') {
          problems.push(`'${k}' must be a function in an action dictionary for '${this.name}'`);
          continue;
        }
        const actual = v.length;
        const expected = this._topDownActionArity(k);
        if (actual !== expected) {
          let details;
          if (k === '_iter' || k === '_nonterminal') {
            details =
              `it should use a rest parameter, e.g. \`${k}(...children) {}\`. ` +
              'NOTE: this is new in Ohm v16 — see https://ohmjs.org/d/ati for details.';
          } else {
            details = `expected ${expected}, got ${actual}`;
          }
          problems.push(`Semantic action '${k}' has the wrong arity: ${details}`);
        }
      }
      if (problems.length > 0) {
        const prettyProblems = problems.map(problem => '- ' + problem);
        const error = new Error(
          [
            `Found errors in the action dictionary of the '${name}' ${what}:`,
            ...prettyProblems,
          ].join('\n')
        );
        error.problems = problems;
        throw error;
      }
    }

    // Return the expected arity for a semantic action named `actionName`, which
    // is either a rule name or a special action name like '_nonterminal'.
    _topDownActionArity(actionName) {
      // All special actions have an expected arity of 0, though all but _terminal
      // are expected to use the rest parameter syntax (e.g. `_iter(...children)`).
      // This is considered to have arity 0, i.e. `((...args) => {}).length` is 0.
      return SPECIAL_ACTION_NAMES.includes(actionName)
        ? 0
        : this.rules[actionName].body.getArity();
    }

    _inheritsFrom(grammar) {
      let g = this.superGrammar;
      while (g) {
        if (g.equals(grammar, true)) {
          return true;
        }
        g = g.superGrammar;
      }
      return false;
    }

    toRecipe(superGrammarExpr = undefined) {
      const metaInfo = {};
      // Include the grammar source if it is available.
      if (this.source) {
        metaInfo.source = this.source.contents;
      }

      let startRule = null;
      if (this.defaultStartRule) {
        startRule = this.defaultStartRule;
      }

      const rules = {};
      Object.keys(this.rules).forEach(ruleName => {
        const ruleInfo = this.rules[ruleName];
        const {body} = ruleInfo;
        const isDefinition = !this.superGrammar || !this.superGrammar.rules[ruleName];

        let operation;
        if (isDefinition) {
          operation = 'define';
        } else {
          operation = body instanceof Extend ? 'extend' : 'override';
        }

        const metaInfo = {};
        if (ruleInfo.source && this.source) {
          const adjusted = ruleInfo.source.relativeTo(this.source);
          metaInfo.sourceInterval = [adjusted.startIdx, adjusted.endIdx];
        }

        const description = isDefinition ? ruleInfo.description : null;
        const bodyRecipe = body.outputRecipe(ruleInfo.formals, this.source);

        rules[ruleName] = [
          operation, // "define"/"extend"/"override"
          metaInfo,
          description,
          ruleInfo.formals,
          bodyRecipe,
        ];
      });

      // If the caller provided an expression to use for the supergrammar, use that.
      // Otherwise, if the supergrammar is a user grammar, use its recipe inline.
      let superGrammarOutput = 'null';
      if (superGrammarExpr) {
        superGrammarOutput = superGrammarExpr;
      } else if (this.superGrammar && !this.superGrammar.isBuiltIn()) {
        superGrammarOutput = this.superGrammar.toRecipe();
      }

      const recipeElements = [
        ...['grammar', metaInfo, this.name].map(JSON.stringify),
        superGrammarOutput,
        ...[startRule, rules].map(JSON.stringify),
      ];
      return jsonToJS(`[${recipeElements.join(',')}]`);
    }

    // TODO: Come up with better names for these methods.
    // TODO: Write the analog of these methods for inherited attributes.
    toOperationActionDictionaryTemplate() {
      return this._toOperationOrAttributeActionDictionaryTemplate();
    }
    toAttributeActionDictionaryTemplate() {
      return this._toOperationOrAttributeActionDictionaryTemplate();
    }

    _toOperationOrAttributeActionDictionaryTemplate() {
      // TODO: add the super-grammar's templates at the right place, e.g., a case for AddExpr_plus
      // should appear next to other cases of AddExpr.

      const sb = new StringBuffer();
      sb.append('{');

      let first = true;

      for (const ruleName in this.rules) {
        const {body} = this.rules[ruleName];
        if (first) {
          first = false;
        } else {
          sb.append(',');
        }
        sb.append('\n');
        sb.append('  ');
        this.addSemanticActionTemplate(ruleName, body, sb);
      }

      sb.append('\n}');
      return sb.contents();
    }

    addSemanticActionTemplate(ruleName, body, sb) {
      sb.append(ruleName);
      sb.append(': function(');
      const arity = this._topDownActionArity(ruleName);
      sb.append(repeat('_', arity).join(', '));
      sb.append(') {\n');
      sb.append('  }');
    }

    // Parse a string which expresses a rule application in this grammar, and return the
    // resulting Apply node.
    parseApplication(str) {
      let app;
      if (str.indexOf('<') === -1) {
        // simple application
        app = new Apply(str);
      } else {
        // parameterized application
        const cst = ohmGrammar$1.match(str, 'Base_application');
        app = buildGrammar$1(cst, {});
      }

      // Ensure that the application is valid.
      if (!(app.ruleName in this.rules)) {
        throw undeclaredRule(app.ruleName, this.name);
      }
      const {formals} = this.rules[app.ruleName];
      if (formals.length !== app.args.length) {
        const {source} = this.rules[app.ruleName];
        throw wrongNumberOfParameters(
          app.ruleName,
          formals.length,
          app.args.length,
          source
        );
      }
      return app;
    }

    _setUpMatchState(state) {
      if (this._matchStateInitializer) {
        this._matchStateInitializer(state);
      }
    }
  }

  // The following grammar contains a few rules that couldn't be written  in "userland".
  // At the bottom of src/main.js, we create a sub-grammar of this grammar that's called
  // `BuiltInRules`. That grammar contains several convenience rules, e.g., `letter` and
  // `digit`, and is implicitly the super-grammar of any grammar whose super-grammar
  // isn't specified.
  Grammar.ProtoBuiltInRules = new Grammar(
    'ProtoBuiltInRules', // name
    undefined, // supergrammar
    {
      any: {
        body: any,
        formals: [],
        description: 'any character',
        primitive: true,
      },
      end: {
        body: end,
        formals: [],
        description: 'end of input',
        primitive: true,
      },

      caseInsensitive: {
        body: new CaseInsensitiveTerminal(new Param(0)),
        formals: ['str'],
        primitive: true,
      },
      lower: {
        body: new UnicodeChar('Ll'),
        formals: [],
        description: 'a lowercase letter',
        primitive: true,
      },
      upper: {
        body: new UnicodeChar('Lu'),
        formals: [],
        description: 'an uppercase letter',
        primitive: true,
      },
      // Union of Lt (titlecase), Lm (modifier), and Lo (other), i.e. any letter not in Ll or Lu.
      unicodeLtmo: {
        body: new UnicodeChar('Ltmo'),
        formals: [],
        description: 'a Unicode character in Lt, Lm, or Lo',
        primitive: true,
      },

      // These rules are not truly primitive (they could be written in userland) but are defined
      // here for bootstrapping purposes.
      spaces: {
        body: new Star(new Apply('space')),
        formals: [],
      },
      space: {
        body: new Range('\x00', ' '),
        formals: [],
        description: 'a space',
      },
    }
  );

  // This method is called from main.js once Ohm has loaded.
  Grammar.initApplicationParser = function (grammar, builderFn) {
    ohmGrammar$1 = grammar;
    buildGrammar$1 = builderFn;
  };

  // --------------------------------------------------------------------
  // Private Stuff
  // --------------------------------------------------------------------

  // Constructors

  class GrammarDecl {
    constructor(name) {
      this.name = name;
    }

    // Helpers

    sourceInterval(startIdx, endIdx) {
      return this.source.subInterval(startIdx, endIdx - startIdx);
    }

    ensureSuperGrammar() {
      if (!this.superGrammar) {
        this.withSuperGrammar(
          // TODO: The conditional expression below is an ugly hack. It's kind of ok because
          // I doubt anyone will ever try to declare a grammar called `BuiltInRules`. Still,
          // we should try to find a better way to do this.
          this.name === 'BuiltInRules' ? Grammar.ProtoBuiltInRules : Grammar.BuiltInRules
        );
      }
      return this.superGrammar;
    }

    ensureSuperGrammarRuleForOverriding(name, source) {
      const ruleInfo = this.ensureSuperGrammar().rules[name];
      if (!ruleInfo) {
        throw cannotOverrideUndeclaredRule(name, this.superGrammar.name, source);
      }
      return ruleInfo;
    }

    installOverriddenOrExtendedRule(name, formals, body, source) {
      const duplicateParameterNames$1 = getDuplicates(formals);
      if (duplicateParameterNames$1.length > 0) {
        throw duplicateParameterNames(name, duplicateParameterNames$1, source);
      }
      const ruleInfo = this.ensureSuperGrammar().rules[name];
      const expectedFormals = ruleInfo.formals;
      const expectedNumFormals = expectedFormals ? expectedFormals.length : 0;
      if (formals.length !== expectedNumFormals) {
        throw wrongNumberOfParameters(name, expectedNumFormals, formals.length, source);
      }
      return this.install(name, formals, body, ruleInfo.description, source);
    }

    install(name, formals, body, description, source, primitive = false) {
      this.rules[name] = {
        body: body.introduceParams(formals),
        formals,
        description,
        source,
        primitive,
      };
      return this;
    }

    // Stuff that you should only do once

    withSuperGrammar(superGrammar) {
      if (this.superGrammar) {
        throw new Error('the super grammar of a GrammarDecl cannot be set more than once');
      }
      this.superGrammar = superGrammar;
      this.rules = Object.create(superGrammar.rules);

      // Grammars with an explicit supergrammar inherit a default start rule.
      if (!superGrammar.isBuiltIn()) {
        this.defaultStartRule = superGrammar.defaultStartRule;
      }
      return this;
    }

    withDefaultStartRule(ruleName) {
      this.defaultStartRule = ruleName;
      return this;
    }

    withSource(source) {
      this.source = new InputStream(source).interval(0, source.length);
      return this;
    }

    // Creates a Grammar instance, and if it passes the sanity checks, returns it.
    build() {
      const grammar = new Grammar(
        this.name,
        this.ensureSuperGrammar(),
        this.rules,
        this.defaultStartRule
      );
      // Initialize internal props that are inherited from the super grammar.
      grammar._matchStateInitializer = grammar.superGrammar._matchStateInitializer;
      grammar.supportsIncrementalParsing = grammar.superGrammar.supportsIncrementalParsing;

      // TODO: change the pexpr.prototype.assert... methods to make them add
      // exceptions to an array that's provided as an arg. Then we'll be able to
      // show more than one error of the same type at a time.
      // TODO: include the offending pexpr in the errors, that way we can show
      // the part of the source that caused it.
      const grammarErrors = [];
      let grammarHasInvalidApplications = false;
      Object.keys(grammar.rules).forEach(ruleName => {
        const {body} = grammar.rules[ruleName];
        try {
          body.assertChoicesHaveUniformArity(ruleName);
        } catch (e) {
          grammarErrors.push(e);
        }
        try {
          body.assertAllApplicationsAreValid(ruleName, grammar);
        } catch (e) {
          grammarErrors.push(e);
          grammarHasInvalidApplications = true;
        }
      });
      if (!grammarHasInvalidApplications) {
        // The following check can only be done if the grammar has no invalid applications.
        Object.keys(grammar.rules).forEach(ruleName => {
          const {body} = grammar.rules[ruleName];
          try {
            body.assertIteratedExprsAreNotNullable(grammar, []);
          } catch (e) {
            grammarErrors.push(e);
          }
        });
      }
      if (grammarErrors.length > 0) {
        throwErrors(grammarErrors);
      }
      if (this.source) {
        grammar.source = this.source;
      }

      return grammar;
    }

    // Rule declarations

    define(name, formals, body, description, source, primitive) {
      this.ensureSuperGrammar();
      if (this.superGrammar.rules[name]) {
        throw duplicateRuleDeclaration(name, this.name, this.superGrammar.name, source);
      } else if (this.rules[name]) {
        throw duplicateRuleDeclaration(name, this.name, this.name, source);
      }
      const duplicateParameterNames$1 = getDuplicates(formals);
      if (duplicateParameterNames$1.length > 0) {
        throw duplicateParameterNames(name, duplicateParameterNames$1, source);
      }
      return this.install(name, formals, body, description, source, primitive);
    }

    override(name, formals, body, descIgnored, source) {
      this.ensureSuperGrammarRuleForOverriding(name, source);
      this.installOverriddenOrExtendedRule(name, formals, body, source);
      return this;
    }

    extend(name, formals, fragment, descIgnored, source) {
      const ruleInfo = this.ensureSuperGrammar().rules[name];
      if (!ruleInfo) {
        throw cannotExtendUndeclaredRule(name, this.superGrammar.name, source);
      }
      const body = new Extend(this.superGrammar, name, fragment);
      body.source = fragment.source;
      this.installOverriddenOrExtendedRule(name, formals, body, source);
      return this;
    }
  }

  // --------------------------------------------------------------------
  // Private stuff
  // --------------------------------------------------------------------

  class Builder {
    constructor(options) {
      this.currentDecl = null;
      this.currentRuleName = null;
      this.options = options || {};
    }

    newGrammar(name) {
      return new GrammarDecl(name);
    }

    grammar(metaInfo, name, superGrammar, defaultStartRule, rules) {
      const gDecl = new GrammarDecl(name);
      if (superGrammar) {
        // `superGrammar` may be a recipe (i.e. an Array), or an actual grammar instance.
        gDecl.withSuperGrammar(
          superGrammar instanceof Grammar ? superGrammar : this.fromRecipe(superGrammar)
        );
      }
      if (defaultStartRule) {
        gDecl.withDefaultStartRule(defaultStartRule);
      }
      if (metaInfo && metaInfo.source) {
        gDecl.withSource(metaInfo.source);
      }

      this.currentDecl = gDecl;
      Object.keys(rules).forEach(ruleName => {
        this.currentRuleName = ruleName;
        const ruleRecipe = rules[ruleName];

        const action = ruleRecipe[0]; // define/extend/override
        const metaInfo = ruleRecipe[1];
        const description = ruleRecipe[2];
        const formals = ruleRecipe[3];
        const body = this.fromRecipe(ruleRecipe[4]);

        let source;
        if (gDecl.source && metaInfo && metaInfo.sourceInterval) {
          source = gDecl.source.subInterval(
            metaInfo.sourceInterval[0],
            metaInfo.sourceInterval[1] - metaInfo.sourceInterval[0]
          );
        }
        gDecl[action](ruleName, formals, body, description, source);
      });
      this.currentRuleName = this.currentDecl = null;
      return gDecl.build();
    }

    terminal(x) {
      return new Terminal(x);
    }

    range(from, to) {
      return new Range(from, to);
    }

    param(index) {
      return new Param(index);
    }

    alt(...termArgs) {
      let terms = [];
      for (let arg of termArgs) {
        if (!(arg instanceof PExpr)) {
          arg = this.fromRecipe(arg);
        }
        if (arg instanceof Alt) {
          terms = terms.concat(arg.terms);
        } else {
          terms.push(arg);
        }
      }
      return terms.length === 1 ? terms[0] : new Alt(terms);
    }

    seq(...factorArgs) {
      let factors = [];
      for (let arg of factorArgs) {
        if (!(arg instanceof PExpr)) {
          arg = this.fromRecipe(arg);
        }
        if (arg instanceof Seq) {
          factors = factors.concat(arg.factors);
        } else {
          factors.push(arg);
        }
      }
      return factors.length === 1 ? factors[0] : new Seq(factors);
    }

    star(expr) {
      if (!(expr instanceof PExpr)) {
        expr = this.fromRecipe(expr);
      }
      return new Star(expr);
    }

    plus(expr) {
      if (!(expr instanceof PExpr)) {
        expr = this.fromRecipe(expr);
      }
      return new Plus(expr);
    }

    opt(expr) {
      if (!(expr instanceof PExpr)) {
        expr = this.fromRecipe(expr);
      }
      return new Opt(expr);
    }

    not(expr) {
      if (!(expr instanceof PExpr)) {
        expr = this.fromRecipe(expr);
      }
      return new Not(expr);
    }

    lookahead(expr) {
      if (!(expr instanceof PExpr)) {
        expr = this.fromRecipe(expr);
      }
      // For v18 compatibility, where we don't want a binding for lookahead.
      if (this.options.eliminateLookaheads) {
        return new Not(new Not(expr));
      }
      return new Lookahead(expr);
    }

    lex(expr) {
      if (!(expr instanceof PExpr)) {
        expr = this.fromRecipe(expr);
      }
      return new Lex(expr);
    }

    app(ruleName, optParams) {
      if (optParams && optParams.length > 0) {
        optParams = optParams.map(function (param) {
          return param instanceof PExpr ? param : this.fromRecipe(param);
        }, this);
      }
      return new Apply(ruleName, optParams);
    }

    // Note that unlike other methods in this class, this method cannot be used as a
    // convenience constructor. It only works with recipes, because it relies on
    // `this.currentDecl` and `this.currentRuleName` being set.
    splice(beforeTerms, afterTerms) {
      return new Splice(
        this.currentDecl.superGrammar,
        this.currentRuleName,
        beforeTerms.map(term => this.fromRecipe(term)),
        afterTerms.map(term => this.fromRecipe(term))
      );
    }

    fromRecipe(recipe) {
      // the meta-info of 'grammar' is processed in Builder.grammar
      const args = recipe[0] === 'grammar' ? recipe.slice(1) : recipe.slice(2);
      const result = this[recipe[0]](...args);

      const metaInfo = recipe[1];
      if (metaInfo) {
        if (metaInfo.sourceInterval && this.currentDecl) {
          result.withSource(this.currentDecl.sourceInterval(...metaInfo.sourceInterval));
        }
      }
      return result;
    }
  }

  function makeRecipe(recipe) {
    if (typeof recipe === 'function') {
      return recipe.call(new Builder());
    } else {
      if (typeof recipe === 'string') {
        // stringified JSON recipe
        recipe = JSON.parse(recipe);
      }
      return new Builder().fromRecipe(recipe);
    }
  }

  var BuiltInRules = makeRecipe(["grammar",{"source":"BuiltInRules {\n\n  alnum  (an alpha-numeric character)\n    = letter\n    | digit\n\n  letter  (a letter)\n    = lower\n    | upper\n    | unicodeLtmo\n\n  digit  (a digit)\n    = \"0\"..\"9\"\n\n  hexDigit  (a hexadecimal digit)\n    = digit\n    | \"a\"..\"f\"\n    | \"A\"..\"F\"\n\n  ListOf<elem, sep>\n    = NonemptyListOf<elem, sep>\n    | EmptyListOf<elem, sep>\n\n  NonemptyListOf<elem, sep>\n    = elem (sep elem)*\n\n  EmptyListOf<elem, sep>\n    = /* nothing */\n\n  listOf<elem, sep>\n    = nonemptyListOf<elem, sep>\n    | emptyListOf<elem, sep>\n\n  nonemptyListOf<elem, sep>\n    = elem (sep elem)*\n\n  emptyListOf<elem, sep>\n    = /* nothing */\n\n  // Allows a syntactic rule application within a lexical context.\n  applySyntactic<app> = app\n}"},"BuiltInRules",null,null,{"alnum":["define",{"sourceInterval":[18,78]},"an alpha-numeric character",[],["alt",{"sourceInterval":[60,78]},["app",{"sourceInterval":[60,66]},"letter",[]],["app",{"sourceInterval":[73,78]},"digit",[]]]],"letter":["define",{"sourceInterval":[82,142]},"a letter",[],["alt",{"sourceInterval":[107,142]},["app",{"sourceInterval":[107,112]},"lower",[]],["app",{"sourceInterval":[119,124]},"upper",[]],["app",{"sourceInterval":[131,142]},"unicodeLtmo",[]]]],"digit":["define",{"sourceInterval":[146,177]},"a digit",[],["range",{"sourceInterval":[169,177]},"0","9"]],"hexDigit":["define",{"sourceInterval":[181,254]},"a hexadecimal digit",[],["alt",{"sourceInterval":[219,254]},["app",{"sourceInterval":[219,224]},"digit",[]],["range",{"sourceInterval":[231,239]},"a","f"],["range",{"sourceInterval":[246,254]},"A","F"]]],"ListOf":["define",{"sourceInterval":[258,336]},null,["elem","sep"],["alt",{"sourceInterval":[282,336]},["app",{"sourceInterval":[282,307]},"NonemptyListOf",[["param",{"sourceInterval":[297,301]},0],["param",{"sourceInterval":[303,306]},1]]],["app",{"sourceInterval":[314,336]},"EmptyListOf",[["param",{"sourceInterval":[326,330]},0],["param",{"sourceInterval":[332,335]},1]]]]],"NonemptyListOf":["define",{"sourceInterval":[340,388]},null,["elem","sep"],["seq",{"sourceInterval":[372,388]},["param",{"sourceInterval":[372,376]},0],["star",{"sourceInterval":[377,388]},["seq",{"sourceInterval":[378,386]},["param",{"sourceInterval":[378,381]},1],["param",{"sourceInterval":[382,386]},0]]]]],"EmptyListOf":["define",{"sourceInterval":[392,434]},null,["elem","sep"],["seq",{"sourceInterval":[438,438]}]],"listOf":["define",{"sourceInterval":[438,516]},null,["elem","sep"],["alt",{"sourceInterval":[462,516]},["app",{"sourceInterval":[462,487]},"nonemptyListOf",[["param",{"sourceInterval":[477,481]},0],["param",{"sourceInterval":[483,486]},1]]],["app",{"sourceInterval":[494,516]},"emptyListOf",[["param",{"sourceInterval":[506,510]},0],["param",{"sourceInterval":[512,515]},1]]]]],"nonemptyListOf":["define",{"sourceInterval":[520,568]},null,["elem","sep"],["seq",{"sourceInterval":[552,568]},["param",{"sourceInterval":[552,556]},0],["star",{"sourceInterval":[557,568]},["seq",{"sourceInterval":[558,566]},["param",{"sourceInterval":[558,561]},1],["param",{"sourceInterval":[562,566]},0]]]]],"emptyListOf":["define",{"sourceInterval":[572,682]},null,["elem","sep"],["seq",{"sourceInterval":[685,685]}]],"applySyntactic":["define",{"sourceInterval":[685,710]},null,["app"],["param",{"sourceInterval":[707,710]},0]]}]);

  Grammar.BuiltInRules = BuiltInRules;
  announceBuiltInRules(Grammar.BuiltInRules);

  var ohmGrammar = makeRecipe(["grammar",{"source":"Ohm {\n\n  Grammars\n    = Grammar*\n\n  Grammar\n    = ident SuperGrammar? \"{\" Rule* \"}\"\n\n  SuperGrammar\n    = \"<:\" ident\n\n  Rule\n    = ident Formals? ruleDescr? \"=\"  RuleBody  -- define\n    | ident Formals?            \":=\" OverrideRuleBody  -- override\n    | ident Formals?            \"+=\" RuleBody  -- extend\n\n  RuleBody\n    = \"|\"? NonemptyListOf<TopLevelTerm, \"|\">\n\n  TopLevelTerm\n    = Seq caseName  -- inline\n    | Seq\n\n  OverrideRuleBody\n    = \"|\"? NonemptyListOf<OverrideTopLevelTerm, \"|\">\n\n  OverrideTopLevelTerm\n    = \"...\"  -- superSplice\n    | TopLevelTerm\n\n  Formals\n    = \"<\" ListOf<ident, \",\"> \">\"\n\n  Params\n    = \"<\" ListOf<Seq, \",\"> \">\"\n\n  Alt\n    = NonemptyListOf<Seq, \"|\">\n\n  Seq\n    = Iter*\n\n  Iter\n    = Pred \"*\"  -- star\n    | Pred \"+\"  -- plus\n    | Pred \"?\"  -- opt\n    | Pred\n\n  Pred\n    = \"~\" Lex  -- not\n    | \"&\" Lex  -- lookahead\n    | Lex\n\n  Lex\n    = \"#\" Base  -- lex\n    | Base\n\n  Base\n    = ident Params? ~(ruleDescr? \"=\" | \":=\" | \"+=\")  -- application\n    | oneCharTerminal \"..\" oneCharTerminal           -- range\n    | terminal                                       -- terminal\n    | \"(\" Alt \")\"                                    -- paren\n\n  ruleDescr  (a rule description)\n    = \"(\" ruleDescrText \")\"\n\n  ruleDescrText\n    = (~\")\" any)*\n\n  caseName\n    = \"--\" (~\"\\n\" space)* name (~\"\\n\" space)* (\"\\n\" | &\"}\")\n\n  name  (a name)\n    = nameFirst nameRest*\n\n  nameFirst\n    = \"_\"\n    | letter\n\n  nameRest\n    = \"_\"\n    | alnum\n\n  ident  (an identifier)\n    = name\n\n  terminal\n    = \"\\\"\" terminalChar* \"\\\"\"\n\n  oneCharTerminal\n    = \"\\\"\" terminalChar \"\\\"\"\n\n  terminalChar\n    = escapeChar\n      | ~\"\\\\\" ~\"\\\"\" ~\"\\n\" \"\\u{0}\"..\"\\u{10FFFF}\"\n\n  escapeChar  (an escape sequence)\n    = \"\\\\\\\\\"                                     -- backslash\n    | \"\\\\\\\"\"                                     -- doubleQuote\n    | \"\\\\\\'\"                                     -- singleQuote\n    | \"\\\\b\"                                      -- backspace\n    | \"\\\\n\"                                      -- lineFeed\n    | \"\\\\r\"                                      -- carriageReturn\n    | \"\\\\t\"                                      -- tab\n    | \"\\\\u{\" hexDigit hexDigit? hexDigit?\n             hexDigit? hexDigit? hexDigit? \"}\"   -- unicodeCodePoint\n    | \"\\\\u\" hexDigit hexDigit hexDigit hexDigit  -- unicodeEscape\n    | \"\\\\x\" hexDigit hexDigit                    -- hexEscape\n\n  space\n   += comment\n\n  comment\n    = \"//\" (~\"\\n\" any)* &(\"\\n\" | end)  -- singleLine\n    | \"/*\" (~\"*/\" any)* \"*/\"  -- multiLine\n\n  tokens = token*\n\n  token = caseName | comment | ident | operator | punctuation | terminal | any\n\n  operator = \"<:\" | \"=\" | \":=\" | \"+=\" | \"*\" | \"+\" | \"?\" | \"~\" | \"&\"\n\n  punctuation = \"<\" | \">\" | \",\" | \"--\"\n}"},"Ohm",null,"Grammars",{"Grammars":["define",{"sourceInterval":[9,32]},null,[],["star",{"sourceInterval":[24,32]},["app",{"sourceInterval":[24,31]},"Grammar",[]]]],"Grammar":["define",{"sourceInterval":[36,83]},null,[],["seq",{"sourceInterval":[50,83]},["app",{"sourceInterval":[50,55]},"ident",[]],["opt",{"sourceInterval":[56,69]},["app",{"sourceInterval":[56,68]},"SuperGrammar",[]]],["terminal",{"sourceInterval":[70,73]},"{"],["star",{"sourceInterval":[74,79]},["app",{"sourceInterval":[74,78]},"Rule",[]]],["terminal",{"sourceInterval":[80,83]},"}"]]],"SuperGrammar":["define",{"sourceInterval":[87,116]},null,[],["seq",{"sourceInterval":[106,116]},["terminal",{"sourceInterval":[106,110]},"<:"],["app",{"sourceInterval":[111,116]},"ident",[]]]],"Rule_define":["define",{"sourceInterval":[131,181]},null,[],["seq",{"sourceInterval":[131,170]},["app",{"sourceInterval":[131,136]},"ident",[]],["opt",{"sourceInterval":[137,145]},["app",{"sourceInterval":[137,144]},"Formals",[]]],["opt",{"sourceInterval":[146,156]},["app",{"sourceInterval":[146,155]},"ruleDescr",[]]],["terminal",{"sourceInterval":[157,160]},"="],["app",{"sourceInterval":[162,170]},"RuleBody",[]]]],"Rule_override":["define",{"sourceInterval":[188,248]},null,[],["seq",{"sourceInterval":[188,235]},["app",{"sourceInterval":[188,193]},"ident",[]],["opt",{"sourceInterval":[194,202]},["app",{"sourceInterval":[194,201]},"Formals",[]]],["terminal",{"sourceInterval":[214,218]},":="],["app",{"sourceInterval":[219,235]},"OverrideRuleBody",[]]]],"Rule_extend":["define",{"sourceInterval":[255,305]},null,[],["seq",{"sourceInterval":[255,294]},["app",{"sourceInterval":[255,260]},"ident",[]],["opt",{"sourceInterval":[261,269]},["app",{"sourceInterval":[261,268]},"Formals",[]]],["terminal",{"sourceInterval":[281,285]},"+="],["app",{"sourceInterval":[286,294]},"RuleBody",[]]]],"Rule":["define",{"sourceInterval":[120,305]},null,[],["alt",{"sourceInterval":[131,305]},["app",{"sourceInterval":[131,170]},"Rule_define",[]],["app",{"sourceInterval":[188,235]},"Rule_override",[]],["app",{"sourceInterval":[255,294]},"Rule_extend",[]]]],"RuleBody":["define",{"sourceInterval":[309,362]},null,[],["seq",{"sourceInterval":[324,362]},["opt",{"sourceInterval":[324,328]},["terminal",{"sourceInterval":[324,327]},"|"]],["app",{"sourceInterval":[329,362]},"NonemptyListOf",[["app",{"sourceInterval":[344,356]},"TopLevelTerm",[]],["terminal",{"sourceInterval":[358,361]},"|"]]]]],"TopLevelTerm_inline":["define",{"sourceInterval":[385,408]},null,[],["seq",{"sourceInterval":[385,397]},["app",{"sourceInterval":[385,388]},"Seq",[]],["app",{"sourceInterval":[389,397]},"caseName",[]]]],"TopLevelTerm":["define",{"sourceInterval":[366,418]},null,[],["alt",{"sourceInterval":[385,418]},["app",{"sourceInterval":[385,397]},"TopLevelTerm_inline",[]],["app",{"sourceInterval":[415,418]},"Seq",[]]]],"OverrideRuleBody":["define",{"sourceInterval":[422,491]},null,[],["seq",{"sourceInterval":[445,491]},["opt",{"sourceInterval":[445,449]},["terminal",{"sourceInterval":[445,448]},"|"]],["app",{"sourceInterval":[450,491]},"NonemptyListOf",[["app",{"sourceInterval":[465,485]},"OverrideTopLevelTerm",[]],["terminal",{"sourceInterval":[487,490]},"|"]]]]],"OverrideTopLevelTerm_superSplice":["define",{"sourceInterval":[522,543]},null,[],["terminal",{"sourceInterval":[522,527]},"..."]],"OverrideTopLevelTerm":["define",{"sourceInterval":[495,562]},null,[],["alt",{"sourceInterval":[522,562]},["app",{"sourceInterval":[522,527]},"OverrideTopLevelTerm_superSplice",[]],["app",{"sourceInterval":[550,562]},"TopLevelTerm",[]]]],"Formals":["define",{"sourceInterval":[566,606]},null,[],["seq",{"sourceInterval":[580,606]},["terminal",{"sourceInterval":[580,583]},"<"],["app",{"sourceInterval":[584,602]},"ListOf",[["app",{"sourceInterval":[591,596]},"ident",[]],["terminal",{"sourceInterval":[598,601]},","]]],["terminal",{"sourceInterval":[603,606]},">"]]],"Params":["define",{"sourceInterval":[610,647]},null,[],["seq",{"sourceInterval":[623,647]},["terminal",{"sourceInterval":[623,626]},"<"],["app",{"sourceInterval":[627,643]},"ListOf",[["app",{"sourceInterval":[634,637]},"Seq",[]],["terminal",{"sourceInterval":[639,642]},","]]],["terminal",{"sourceInterval":[644,647]},">"]]],"Alt":["define",{"sourceInterval":[651,685]},null,[],["app",{"sourceInterval":[661,685]},"NonemptyListOf",[["app",{"sourceInterval":[676,679]},"Seq",[]],["terminal",{"sourceInterval":[681,684]},"|"]]]],"Seq":["define",{"sourceInterval":[689,704]},null,[],["star",{"sourceInterval":[699,704]},["app",{"sourceInterval":[699,703]},"Iter",[]]]],"Iter_star":["define",{"sourceInterval":[719,736]},null,[],["seq",{"sourceInterval":[719,727]},["app",{"sourceInterval":[719,723]},"Pred",[]],["terminal",{"sourceInterval":[724,727]},"*"]]],"Iter_plus":["define",{"sourceInterval":[743,760]},null,[],["seq",{"sourceInterval":[743,751]},["app",{"sourceInterval":[743,747]},"Pred",[]],["terminal",{"sourceInterval":[748,751]},"+"]]],"Iter_opt":["define",{"sourceInterval":[767,783]},null,[],["seq",{"sourceInterval":[767,775]},["app",{"sourceInterval":[767,771]},"Pred",[]],["terminal",{"sourceInterval":[772,775]},"?"]]],"Iter":["define",{"sourceInterval":[708,794]},null,[],["alt",{"sourceInterval":[719,794]},["app",{"sourceInterval":[719,727]},"Iter_star",[]],["app",{"sourceInterval":[743,751]},"Iter_plus",[]],["app",{"sourceInterval":[767,775]},"Iter_opt",[]],["app",{"sourceInterval":[790,794]},"Pred",[]]]],"Pred_not":["define",{"sourceInterval":[809,824]},null,[],["seq",{"sourceInterval":[809,816]},["terminal",{"sourceInterval":[809,812]},"~"],["app",{"sourceInterval":[813,816]},"Lex",[]]]],"Pred_lookahead":["define",{"sourceInterval":[831,852]},null,[],["seq",{"sourceInterval":[831,838]},["terminal",{"sourceInterval":[831,834]},"&"],["app",{"sourceInterval":[835,838]},"Lex",[]]]],"Pred":["define",{"sourceInterval":[798,862]},null,[],["alt",{"sourceInterval":[809,862]},["app",{"sourceInterval":[809,816]},"Pred_not",[]],["app",{"sourceInterval":[831,838]},"Pred_lookahead",[]],["app",{"sourceInterval":[859,862]},"Lex",[]]]],"Lex_lex":["define",{"sourceInterval":[876,892]},null,[],["seq",{"sourceInterval":[876,884]},["terminal",{"sourceInterval":[876,879]},"#"],["app",{"sourceInterval":[880,884]},"Base",[]]]],"Lex":["define",{"sourceInterval":[866,903]},null,[],["alt",{"sourceInterval":[876,903]},["app",{"sourceInterval":[876,884]},"Lex_lex",[]],["app",{"sourceInterval":[899,903]},"Base",[]]]],"Base_application":["define",{"sourceInterval":[918,979]},null,[],["seq",{"sourceInterval":[918,963]},["app",{"sourceInterval":[918,923]},"ident",[]],["opt",{"sourceInterval":[924,931]},["app",{"sourceInterval":[924,930]},"Params",[]]],["not",{"sourceInterval":[932,963]},["alt",{"sourceInterval":[934,962]},["seq",{"sourceInterval":[934,948]},["opt",{"sourceInterval":[934,944]},["app",{"sourceInterval":[934,943]},"ruleDescr",[]]],["terminal",{"sourceInterval":[945,948]},"="]],["terminal",{"sourceInterval":[951,955]},":="],["terminal",{"sourceInterval":[958,962]},"+="]]]]],"Base_range":["define",{"sourceInterval":[986,1041]},null,[],["seq",{"sourceInterval":[986,1022]},["app",{"sourceInterval":[986,1001]},"oneCharTerminal",[]],["terminal",{"sourceInterval":[1002,1006]},".."],["app",{"sourceInterval":[1007,1022]},"oneCharTerminal",[]]]],"Base_terminal":["define",{"sourceInterval":[1048,1106]},null,[],["app",{"sourceInterval":[1048,1056]},"terminal",[]]],"Base_paren":["define",{"sourceInterval":[1113,1168]},null,[],["seq",{"sourceInterval":[1113,1124]},["terminal",{"sourceInterval":[1113,1116]},"("],["app",{"sourceInterval":[1117,1120]},"Alt",[]],["terminal",{"sourceInterval":[1121,1124]},")"]]],"Base":["define",{"sourceInterval":[907,1168]},null,[],["alt",{"sourceInterval":[918,1168]},["app",{"sourceInterval":[918,963]},"Base_application",[]],["app",{"sourceInterval":[986,1022]},"Base_range",[]],["app",{"sourceInterval":[1048,1056]},"Base_terminal",[]],["app",{"sourceInterval":[1113,1124]},"Base_paren",[]]]],"ruleDescr":["define",{"sourceInterval":[1172,1231]},"a rule description",[],["seq",{"sourceInterval":[1210,1231]},["terminal",{"sourceInterval":[1210,1213]},"("],["app",{"sourceInterval":[1214,1227]},"ruleDescrText",[]],["terminal",{"sourceInterval":[1228,1231]},")"]]],"ruleDescrText":["define",{"sourceInterval":[1235,1266]},null,[],["star",{"sourceInterval":[1255,1266]},["seq",{"sourceInterval":[1256,1264]},["not",{"sourceInterval":[1256,1260]},["terminal",{"sourceInterval":[1257,1260]},")"]],["app",{"sourceInterval":[1261,1264]},"any",[]]]]],"caseName":["define",{"sourceInterval":[1270,1338]},null,[],["seq",{"sourceInterval":[1285,1338]},["terminal",{"sourceInterval":[1285,1289]},"--"],["star",{"sourceInterval":[1290,1304]},["seq",{"sourceInterval":[1291,1302]},["not",{"sourceInterval":[1291,1296]},["terminal",{"sourceInterval":[1292,1296]},"\n"]],["app",{"sourceInterval":[1297,1302]},"space",[]]]],["app",{"sourceInterval":[1305,1309]},"name",[]],["star",{"sourceInterval":[1310,1324]},["seq",{"sourceInterval":[1311,1322]},["not",{"sourceInterval":[1311,1316]},["terminal",{"sourceInterval":[1312,1316]},"\n"]],["app",{"sourceInterval":[1317,1322]},"space",[]]]],["alt",{"sourceInterval":[1326,1337]},["terminal",{"sourceInterval":[1326,1330]},"\n"],["lookahead",{"sourceInterval":[1333,1337]},["terminal",{"sourceInterval":[1334,1337]},"}"]]]]],"name":["define",{"sourceInterval":[1342,1382]},"a name",[],["seq",{"sourceInterval":[1363,1382]},["app",{"sourceInterval":[1363,1372]},"nameFirst",[]],["star",{"sourceInterval":[1373,1382]},["app",{"sourceInterval":[1373,1381]},"nameRest",[]]]]],"nameFirst":["define",{"sourceInterval":[1386,1418]},null,[],["alt",{"sourceInterval":[1402,1418]},["terminal",{"sourceInterval":[1402,1405]},"_"],["app",{"sourceInterval":[1412,1418]},"letter",[]]]],"nameRest":["define",{"sourceInterval":[1422,1452]},null,[],["alt",{"sourceInterval":[1437,1452]},["terminal",{"sourceInterval":[1437,1440]},"_"],["app",{"sourceInterval":[1447,1452]},"alnum",[]]]],"ident":["define",{"sourceInterval":[1456,1489]},"an identifier",[],["app",{"sourceInterval":[1485,1489]},"name",[]]],"terminal":["define",{"sourceInterval":[1493,1531]},null,[],["seq",{"sourceInterval":[1508,1531]},["terminal",{"sourceInterval":[1508,1512]},"\""],["star",{"sourceInterval":[1513,1526]},["app",{"sourceInterval":[1513,1525]},"terminalChar",[]]],["terminal",{"sourceInterval":[1527,1531]},"\""]]],"oneCharTerminal":["define",{"sourceInterval":[1535,1579]},null,[],["seq",{"sourceInterval":[1557,1579]},["terminal",{"sourceInterval":[1557,1561]},"\""],["app",{"sourceInterval":[1562,1574]},"terminalChar",[]],["terminal",{"sourceInterval":[1575,1579]},"\""]]],"terminalChar":["define",{"sourceInterval":[1583,1660]},null,[],["alt",{"sourceInterval":[1602,1660]},["app",{"sourceInterval":[1602,1612]},"escapeChar",[]],["seq",{"sourceInterval":[1621,1660]},["not",{"sourceInterval":[1621,1626]},["terminal",{"sourceInterval":[1622,1626]},"\\"]],["not",{"sourceInterval":[1627,1632]},["terminal",{"sourceInterval":[1628,1632]},"\""]],["not",{"sourceInterval":[1633,1638]},["terminal",{"sourceInterval":[1634,1638]},"\n"]],["range",{"sourceInterval":[1639,1660]},"\u0000","􏿿"]]]],"escapeChar_backslash":["define",{"sourceInterval":[1703,1758]},null,[],["terminal",{"sourceInterval":[1703,1709]},"\\\\"]],"escapeChar_doubleQuote":["define",{"sourceInterval":[1765,1822]},null,[],["terminal",{"sourceInterval":[1765,1771]},"\\\""]],"escapeChar_singleQuote":["define",{"sourceInterval":[1829,1886]},null,[],["terminal",{"sourceInterval":[1829,1835]},"\\'"]],"escapeChar_backspace":["define",{"sourceInterval":[1893,1948]},null,[],["terminal",{"sourceInterval":[1893,1898]},"\\b"]],"escapeChar_lineFeed":["define",{"sourceInterval":[1955,2009]},null,[],["terminal",{"sourceInterval":[1955,1960]},"\\n"]],"escapeChar_carriageReturn":["define",{"sourceInterval":[2016,2076]},null,[],["terminal",{"sourceInterval":[2016,2021]},"\\r"]],"escapeChar_tab":["define",{"sourceInterval":[2083,2132]},null,[],["terminal",{"sourceInterval":[2083,2088]},"\\t"]],"escapeChar_unicodeCodePoint":["define",{"sourceInterval":[2139,2243]},null,[],["seq",{"sourceInterval":[2139,2221]},["terminal",{"sourceInterval":[2139,2145]},"\\u{"],["app",{"sourceInterval":[2146,2154]},"hexDigit",[]],["opt",{"sourceInterval":[2155,2164]},["app",{"sourceInterval":[2155,2163]},"hexDigit",[]]],["opt",{"sourceInterval":[2165,2174]},["app",{"sourceInterval":[2165,2173]},"hexDigit",[]]],["opt",{"sourceInterval":[2188,2197]},["app",{"sourceInterval":[2188,2196]},"hexDigit",[]]],["opt",{"sourceInterval":[2198,2207]},["app",{"sourceInterval":[2198,2206]},"hexDigit",[]]],["opt",{"sourceInterval":[2208,2217]},["app",{"sourceInterval":[2208,2216]},"hexDigit",[]]],["terminal",{"sourceInterval":[2218,2221]},"}"]]],"escapeChar_unicodeEscape":["define",{"sourceInterval":[2250,2309]},null,[],["seq",{"sourceInterval":[2250,2291]},["terminal",{"sourceInterval":[2250,2255]},"\\u"],["app",{"sourceInterval":[2256,2264]},"hexDigit",[]],["app",{"sourceInterval":[2265,2273]},"hexDigit",[]],["app",{"sourceInterval":[2274,2282]},"hexDigit",[]],["app",{"sourceInterval":[2283,2291]},"hexDigit",[]]]],"escapeChar_hexEscape":["define",{"sourceInterval":[2316,2371]},null,[],["seq",{"sourceInterval":[2316,2339]},["terminal",{"sourceInterval":[2316,2321]},"\\x"],["app",{"sourceInterval":[2322,2330]},"hexDigit",[]],["app",{"sourceInterval":[2331,2339]},"hexDigit",[]]]],"escapeChar":["define",{"sourceInterval":[1664,2371]},"an escape sequence",[],["alt",{"sourceInterval":[1703,2371]},["app",{"sourceInterval":[1703,1709]},"escapeChar_backslash",[]],["app",{"sourceInterval":[1765,1771]},"escapeChar_doubleQuote",[]],["app",{"sourceInterval":[1829,1835]},"escapeChar_singleQuote",[]],["app",{"sourceInterval":[1893,1898]},"escapeChar_backspace",[]],["app",{"sourceInterval":[1955,1960]},"escapeChar_lineFeed",[]],["app",{"sourceInterval":[2016,2021]},"escapeChar_carriageReturn",[]],["app",{"sourceInterval":[2083,2088]},"escapeChar_tab",[]],["app",{"sourceInterval":[2139,2221]},"escapeChar_unicodeCodePoint",[]],["app",{"sourceInterval":[2250,2291]},"escapeChar_unicodeEscape",[]],["app",{"sourceInterval":[2316,2339]},"escapeChar_hexEscape",[]]]],"space":["extend",{"sourceInterval":[2375,2394]},null,[],["app",{"sourceInterval":[2387,2394]},"comment",[]]],"comment_singleLine":["define",{"sourceInterval":[2412,2458]},null,[],["seq",{"sourceInterval":[2412,2443]},["terminal",{"sourceInterval":[2412,2416]},"//"],["star",{"sourceInterval":[2417,2429]},["seq",{"sourceInterval":[2418,2427]},["not",{"sourceInterval":[2418,2423]},["terminal",{"sourceInterval":[2419,2423]},"\n"]],["app",{"sourceInterval":[2424,2427]},"any",[]]]],["lookahead",{"sourceInterval":[2430,2443]},["alt",{"sourceInterval":[2432,2442]},["terminal",{"sourceInterval":[2432,2436]},"\n"],["app",{"sourceInterval":[2439,2442]},"end",[]]]]]],"comment_multiLine":["define",{"sourceInterval":[2465,2501]},null,[],["seq",{"sourceInterval":[2465,2487]},["terminal",{"sourceInterval":[2465,2469]},"/*"],["star",{"sourceInterval":[2470,2482]},["seq",{"sourceInterval":[2471,2480]},["not",{"sourceInterval":[2471,2476]},["terminal",{"sourceInterval":[2472,2476]},"*/"]],["app",{"sourceInterval":[2477,2480]},"any",[]]]],["terminal",{"sourceInterval":[2483,2487]},"*/"]]],"comment":["define",{"sourceInterval":[2398,2501]},null,[],["alt",{"sourceInterval":[2412,2501]},["app",{"sourceInterval":[2412,2443]},"comment_singleLine",[]],["app",{"sourceInterval":[2465,2487]},"comment_multiLine",[]]]],"tokens":["define",{"sourceInterval":[2505,2520]},null,[],["star",{"sourceInterval":[2514,2520]},["app",{"sourceInterval":[2514,2519]},"token",[]]]],"token":["define",{"sourceInterval":[2524,2600]},null,[],["alt",{"sourceInterval":[2532,2600]},["app",{"sourceInterval":[2532,2540]},"caseName",[]],["app",{"sourceInterval":[2543,2550]},"comment",[]],["app",{"sourceInterval":[2553,2558]},"ident",[]],["app",{"sourceInterval":[2561,2569]},"operator",[]],["app",{"sourceInterval":[2572,2583]},"punctuation",[]],["app",{"sourceInterval":[2586,2594]},"terminal",[]],["app",{"sourceInterval":[2597,2600]},"any",[]]]],"operator":["define",{"sourceInterval":[2604,2669]},null,[],["alt",{"sourceInterval":[2615,2669]},["terminal",{"sourceInterval":[2615,2619]},"<:"],["terminal",{"sourceInterval":[2622,2625]},"="],["terminal",{"sourceInterval":[2628,2632]},":="],["terminal",{"sourceInterval":[2635,2639]},"+="],["terminal",{"sourceInterval":[2642,2645]},"*"],["terminal",{"sourceInterval":[2648,2651]},"+"],["terminal",{"sourceInterval":[2654,2657]},"?"],["terminal",{"sourceInterval":[2660,2663]},"~"],["terminal",{"sourceInterval":[2666,2669]},"&"]]],"punctuation":["define",{"sourceInterval":[2673,2709]},null,[],["alt",{"sourceInterval":[2687,2709]},["terminal",{"sourceInterval":[2687,2690]},"<"],["terminal",{"sourceInterval":[2693,2696]},">"],["terminal",{"sourceInterval":[2699,2702]},","],["terminal",{"sourceInterval":[2705,2709]},"--"]]]}]);

  const superSplicePlaceholder = Object.create(PExpr.prototype);

  function namespaceHas(ns, name) {
    // Look for an enumerable property, anywhere in the prototype chain.
    for (const prop in ns) {
      if (prop === name) return true;
    }
    return false;
  }

  // Returns a Grammar instance (i.e., an object with a `match` method) for
  // `tree`, which is the concrete syntax tree of a user-written grammar.
  // The grammar will be assigned into `namespace` under the name of the grammar
  // as specified in the source.
  function buildGrammar(match, namespace, optOhmGrammarForTesting, options) {
    const builder = new Builder(options);
    let decl;
    let currentRuleName;
    let currentRuleFormals;
    let overriding = false;
    const metaGrammar = optOhmGrammarForTesting || ohmGrammar;

    // A visitor that produces a Grammar instance from the CST.
    const helpers = metaGrammar.createSemantics().addOperation('visit', {
      Grammars(grammarIter) {
        return grammarIter.children.map(c => c.visit());
      },
      Grammar(id, s, _open, rules, _close) {
        const grammarName = id.visit();
        decl = builder.newGrammar(grammarName);
        s.child(0) && s.child(0).visit();
        rules.children.map(c => c.visit());
        const g = decl.build();
        g.source = this.source.trimmed();
        if (namespaceHas(namespace, grammarName)) {
          throw duplicateGrammarDeclaration(g);
        }
        namespace[grammarName] = g;
        return g;
      },

      SuperGrammar(_, n) {
        const superGrammarName = n.visit();
        if (superGrammarName === 'null') {
          decl.withSuperGrammar(null);
        } else {
          if (!namespace || !namespaceHas(namespace, superGrammarName)) {
            throw undeclaredGrammar(superGrammarName, namespace, n.source);
          }
          decl.withSuperGrammar(namespace[superGrammarName]);
        }
      },

      Rule_define(n, fs, d, _, b) {
        currentRuleName = n.visit();
        currentRuleFormals = fs.children.map(c => c.visit())[0] || [];
        // If there is no default start rule yet, set it now. This must be done before visiting
        // the body, because it might contain an inline rule definition.
        if (!decl.defaultStartRule && decl.ensureSuperGrammar() !== Grammar.ProtoBuiltInRules) {
          decl.withDefaultStartRule(currentRuleName);
        }
        const body = b.visit();
        const description = d.children.map(c => c.visit())[0];
        const source = this.source.trimmed();
        return decl.define(currentRuleName, currentRuleFormals, body, description, source);
      },
      Rule_override(n, fs, _, b) {
        currentRuleName = n.visit();
        currentRuleFormals = fs.children.map(c => c.visit())[0] || [];

        const source = this.source.trimmed();
        decl.ensureSuperGrammarRuleForOverriding(currentRuleName, source);

        overriding = true;
        const body = b.visit();
        overriding = false;
        return decl.override(currentRuleName, currentRuleFormals, body, null, source);
      },
      Rule_extend(n, fs, _, b) {
        currentRuleName = n.visit();
        currentRuleFormals = fs.children.map(c => c.visit())[0] || [];
        const body = b.visit();
        const source = this.source.trimmed();
        return decl.extend(currentRuleName, currentRuleFormals, body, null, source);
      },
      RuleBody(_, terms) {
        return builder.alt(...terms.visit()).withSource(this.source);
      },
      OverrideRuleBody(_, terms) {
        const args = terms.visit();

        // Check if the super-splice operator (`...`) appears in the terms.
        const expansionPos = args.indexOf(superSplicePlaceholder);
        if (expansionPos >= 0) {
          const beforeTerms = args.slice(0, expansionPos);
          const afterTerms = args.slice(expansionPos + 1);

          // Ensure it appears no more than once.
          afterTerms.forEach(t => {
            if (t === superSplicePlaceholder) throw multipleSuperSplices(t);
          });

          return new Splice(
            decl.superGrammar,
            currentRuleName,
            beforeTerms,
            afterTerms
          ).withSource(this.source);
        } else {
          return builder.alt(...args).withSource(this.source);
        }
      },
      Formals(opointy, fs, cpointy) {
        return fs.visit();
      },

      Params(opointy, ps, cpointy) {
        return ps.visit();
      },

      Alt(seqs) {
        return builder.alt(...seqs.visit()).withSource(this.source);
      },

      TopLevelTerm_inline(b, n) {
        const inlineRuleName = currentRuleName + '_' + n.visit();
        const body = b.visit();
        const source = this.source.trimmed();
        const isNewRuleDeclaration = !(
          decl.superGrammar && decl.superGrammar.rules[inlineRuleName]
        );
        if (overriding && !isNewRuleDeclaration) {
          decl.override(inlineRuleName, currentRuleFormals, body, null, source);
        } else {
          decl.define(inlineRuleName, currentRuleFormals, body, null, source);
        }
        const params = currentRuleFormals.map(formal => builder.app(formal));
        return builder.app(inlineRuleName, params).withSource(body.source);
      },
      OverrideTopLevelTerm_superSplice(_) {
        return superSplicePlaceholder;
      },

      Seq(expr) {
        return builder.seq(...expr.children.map(c => c.visit())).withSource(this.source);
      },

      Iter_star(x, _) {
        return builder.star(x.visit()).withSource(this.source);
      },
      Iter_plus(x, _) {
        return builder.plus(x.visit()).withSource(this.source);
      },
      Iter_opt(x, _) {
        return builder.opt(x.visit()).withSource(this.source);
      },

      Pred_not(_, x) {
        return builder.not(x.visit()).withSource(this.source);
      },
      Pred_lookahead(_, x) {
        return builder.lookahead(x.visit()).withSource(this.source);
      },

      Lex_lex(_, x) {
        return builder.lex(x.visit()).withSource(this.source);
      },

      Base_application(rule, ps) {
        const params = ps.children.map(c => c.visit())[0] || [];
        return builder.app(rule.visit(), params).withSource(this.source);
      },
      Base_range(from, _, to) {
        return builder.range(from.visit(), to.visit()).withSource(this.source);
      },
      Base_terminal(expr) {
        return builder.terminal(expr.visit()).withSource(this.source);
      },
      Base_paren(open, x, close) {
        return x.visit();
      },

      ruleDescr(open, t, close) {
        return t.visit();
      },
      ruleDescrText(_) {
        return this.sourceString.trim();
      },

      caseName(_, space1, n, space2, end) {
        return n.visit();
      },

      name(first, rest) {
        return this.sourceString;
      },
      nameFirst(expr) {},
      nameRest(expr) {},

      terminal(open, cs, close) {
        return cs.children.map(c => c.visit()).join('');
      },

      oneCharTerminal(open, c, close) {
        return c.visit();
      },

      escapeChar(c) {
        try {
          return unescapeCodePoint(this.sourceString);
        } catch (err) {
          if (err instanceof RangeError && err.message.startsWith('Invalid code point ')) {
            throw invalidCodePoint(c);
          }
          throw err; // Rethrow
        }
      },

      NonemptyListOf(x, _, xs) {
        return [x.visit()].concat(xs.children.map(c => c.visit()));
      },
      EmptyListOf() {
        return [];
      },

      _terminal() {
        return this.sourceString;
      },
    });
    return helpers(match).visit();
  }

  var operationsAndAttributesGrammar = makeRecipe(["grammar",{"source":"OperationsAndAttributes {\n\n  AttributeSignature =\n    name\n\n  OperationSignature =\n    name Formals?\n\n  Formals\n    = \"(\" ListOf<name, \",\"> \")\"\n\n  name  (a name)\n    = nameFirst nameRest*\n\n  nameFirst\n    = \"_\"\n    | letter\n\n  nameRest\n    = \"_\"\n    | alnum\n\n}"},"OperationsAndAttributes",null,"AttributeSignature",{"AttributeSignature":["define",{"sourceInterval":[29,58]},null,[],["app",{"sourceInterval":[54,58]},"name",[]]],"OperationSignature":["define",{"sourceInterval":[62,100]},null,[],["seq",{"sourceInterval":[87,100]},["app",{"sourceInterval":[87,91]},"name",[]],["opt",{"sourceInterval":[92,100]},["app",{"sourceInterval":[92,99]},"Formals",[]]]]],"Formals":["define",{"sourceInterval":[104,143]},null,[],["seq",{"sourceInterval":[118,143]},["terminal",{"sourceInterval":[118,121]},"("],["app",{"sourceInterval":[122,139]},"ListOf",[["app",{"sourceInterval":[129,133]},"name",[]],["terminal",{"sourceInterval":[135,138]},","]]],["terminal",{"sourceInterval":[140,143]},")"]]],"name":["define",{"sourceInterval":[147,187]},"a name",[],["seq",{"sourceInterval":[168,187]},["app",{"sourceInterval":[168,177]},"nameFirst",[]],["star",{"sourceInterval":[178,187]},["app",{"sourceInterval":[178,186]},"nameRest",[]]]]],"nameFirst":["define",{"sourceInterval":[191,223]},null,[],["alt",{"sourceInterval":[207,223]},["terminal",{"sourceInterval":[207,210]},"_"],["app",{"sourceInterval":[217,223]},"letter",[]]]],"nameRest":["define",{"sourceInterval":[227,257]},null,[],["alt",{"sourceInterval":[242,257]},["terminal",{"sourceInterval":[242,245]},"_"],["app",{"sourceInterval":[252,257]},"alnum",[]]]]}]);

  initBuiltInSemantics(Grammar.BuiltInRules);
  initPrototypeParser(operationsAndAttributesGrammar); // requires BuiltInSemantics

  function initBuiltInSemantics(builtInRules) {
    const actions = {
      empty() {
        return this.iteration();
      },
      nonEmpty(first, _, rest) {
        return this.iteration([first].concat(rest.children));
      },
      self(..._children) {
        return this;
      },
    };

    Semantics.BuiltInSemantics = Semantics.createSemantics(builtInRules, null).addOperation(
      'asIteration',
      {
        emptyListOf: actions.empty,
        nonemptyListOf: actions.nonEmpty,
        EmptyListOf: actions.empty,
        NonemptyListOf: actions.nonEmpty,
        _iter: actions.self,
      }
    );
  }

  function initPrototypeParser(grammar) {
    Semantics.prototypeGrammarSemantics = grammar.createSemantics().addOperation('parse', {
      AttributeSignature(name) {
        return {
          name: name.parse(),
          formals: [],
        };
      },
      OperationSignature(name, optFormals) {
        return {
          name: name.parse(),
          formals: optFormals.children.map(c => c.parse())[0] || [],
        };
      },
      Formals(oparen, fs, cparen) {
        return fs.asIteration().children.map(c => c.parse());
      },
      name(first, rest) {
        return this.sourceString;
      },
    });
    Semantics.prototypeGrammar = grammar;
  }

  function findIndentation(input) {
    let pos = 0;
    const stack = [0];
    const topOfStack = () => stack[stack.length - 1];

    const result = {};

    const regex = /( *).*(?:$|\r?\n|\r)/g;
    let match;
    while ((match = regex.exec(input)) != null) {
      const [line, indent] = match;

      // The last match will always have length 0. In every other case, some
      // characters will be matched (possibly only the end of line chars).
      if (line.length === 0) break;

      const indentSize = indent.length;
      const prevSize = topOfStack();

      const indentPos = pos + indentSize;

      if (indentSize > prevSize) {
        // Indent -- always only 1.
        stack.push(indentSize);
        result[indentPos] = 1;
      } else if (indentSize < prevSize) {
        // Dedent -- can be multiple levels.
        const prevLength = stack.length;
        while (topOfStack() !== indentSize) {
          stack.pop();
        }
        result[indentPos] = -1 * (prevLength - stack.length);
      }
      pos += line.length;
    }
    // Ensure that there is a matching DEDENT for every remaining INDENT.
    if (stack.length > 1) {
      result[pos] = 1 - stack.length;
    }
    return result;
  }

  const INDENT_DESCRIPTION = 'an indented block';
  const DEDENT_DESCRIPTION = 'a dedent';

  // A sentinel value that is out of range for both charCodeAt() and codePointAt().
  const INVALID_CODE_POINT = 0x10ffff + 1;

  class InputStreamWithIndentation extends InputStream {
    constructor(state) {
      super(state.input);
      this.state = state;
    }

    _indentationAt(pos) {
      return this.state.userData[pos] || 0;
    }

    atEnd() {
      return super.atEnd() && this._indentationAt(this.pos) === 0;
    }

    next() {
      if (this._indentationAt(this.pos) !== 0) {
        this.examinedLength = Math.max(this.examinedLength, this.pos);
        return undefined;
      }
      return super.next();
    }

    nextCharCode() {
      if (this._indentationAt(this.pos) !== 0) {
        this.examinedLength = Math.max(this.examinedLength, this.pos);
        return INVALID_CODE_POINT;
      }
      return super.nextCharCode();
    }

    nextCodePoint() {
      if (this._indentationAt(this.pos) !== 0) {
        this.examinedLength = Math.max(this.examinedLength, this.pos);
        return INVALID_CODE_POINT;
      }
      return super.nextCodePoint();
    }
  }

  class Indentation extends PExpr {
    constructor(isIndent = true) {
      super();
      this.isIndent = isIndent;
    }

    allowsSkippingPrecedingSpace() {
      return true;
    }

    eval(state) {
      const {inputStream} = state;
      const pseudoTokens = state.userData;
      state.doNotMemoize = true;

      const origPos = inputStream.pos;

      const sign = this.isIndent ? 1 : -1;
      const count = (pseudoTokens[origPos] || 0) * sign;
      if (count > 0) {
        // Update the count to consume the pseudotoken.
        state.userData = Object.create(pseudoTokens);
        state.userData[origPos] -= sign;

        state.pushBinding(new TerminalNode(0), origPos);
        return true;
      } else {
        state.processFailure(origPos, this);
        return false;
      }
    }

    getArity() {
      return 1;
    }

    _assertAllApplicationsAreValid(ruleName, grammar) {}

    _isNullable(grammar, memo) {
      return false;
    }

    assertChoicesHaveUniformArity(ruleName) {}

    assertIteratedExprsAreNotNullable(grammar) {}

    introduceParams(formals) {
      return this;
    }

    substituteParams(actuals) {
      return this;
    }

    toString() {
      return this.isIndent ? 'indent' : 'dedent';
    }

    toDisplayString() {
      return this.toString();
    }

    toFailure(grammar) {
      const description = this.isIndent ? INDENT_DESCRIPTION : DEDENT_DESCRIPTION;
      return new Failure(this, description, 'description');
    }
  }

  // Create a new definition for `any` that can consume indent & dedent.
  const applyIndent = new Apply('indent');
  const applyDedent = new Apply('dedent');
  const newAnyBody = new Splice(BuiltInRules, 'any', [applyIndent, applyDedent], []);

  const IndentationSensitive = new Builder()
    .newGrammar('IndentationSensitive')
    .withSuperGrammar(BuiltInRules)
    .define('indent', [], new Indentation(true), INDENT_DESCRIPTION, undefined, true)
    .define('dedent', [], new Indentation(false), DEDENT_DESCRIPTION, undefined, true)
    .extend('any', [], newAnyBody, 'any character', undefined)
    .build();

  Object.assign(IndentationSensitive, {
    _matchStateInitializer(state) {
      state.userData = findIndentation(state.input);
      state.inputStream = new InputStreamWithIndentation(state);
    },
    supportsIncrementalParsing: false,
  });

  // Generated by scripts/prebuild.js
  const version = '17.5.0';

  Grammar.initApplicationParser(ohmGrammar, buildGrammar);

  const isBuffer = obj =>
    !!obj.constructor &&
    typeof obj.constructor.isBuffer === 'function' &&
    obj.constructor.isBuffer(obj);

  function compileAndLoad(source, namespace, buildOptions) {
    const m = ohmGrammar.match(source, 'Grammars');
    if (m.failed()) {
      throw grammarSyntaxError(m);
    }
    return buildGrammar(m, namespace, undefined, buildOptions);
  }

  function _grammar(source, optNamespace, buildOptions) {
    const ns = _grammars(source, optNamespace, buildOptions);

    // Ensure that the source contained no more than one grammar definition.
    const grammarNames = Object.keys(ns);
    if (grammarNames.length === 0) {
      throw new Error('Missing grammar definition');
    } else if (grammarNames.length > 1) {
      const secondGrammar = ns[grammarNames[1]];
      const interval = secondGrammar.source;
      throw new Error(
        getLineAndColumnMessage(interval.sourceString, interval.startIdx) +
          'Found more than one grammar definition -- use ohm.grammars() instead.'
      );
    }
    return ns[grammarNames[0]]; // Return the one and only grammar.
  }

  function _grammars(source, optNamespace, buildOptions) {
    const ns = Object.create(optNamespace || {});
    if (typeof source !== 'string') {
      // For convenience, detect Node.js Buffer objects and automatically call toString().
      if (isBuffer(source)) {
        source = source.toString();
      } else {
        throw new TypeError(
          'Expected string as first argument, got ' + unexpectedObjToString(source)
        );
      }
    }
    compileAndLoad(source, ns, buildOptions);
    return ns;
  }

  function grammar(source, optNamespace) {
    return _grammar(source, optNamespace);
  }

  function grammars(source, optNamespace) {
    return _grammars(source, optNamespace);
  }

  exports.ExperimentalIndentationSensitive = IndentationSensitive;
  exports._buildGrammar = buildGrammar;
  exports.grammar = grammar;
  exports.grammars = grammars;
  exports.makeRecipe = makeRecipe;
  exports.ohmGrammar = ohmGrammar;
  exports.pexprs = pexprs;
  exports.version = version;

  Object.defineProperty(exports, '__esModule', { value: true });

}));
//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoib2htLmpzIiwic291cmNlcyI6WyIuLi9zcmMvY29tbW9uLmpzIiwiLi4vc3JjL3VuaWNvZGUuanMiLCIuLi9zcmMvcGV4cHJzLW1haW4uanMiLCIuLi9zcmMvZXJyb3JzLmpzIiwiLi4vc3JjL3V0aWwuanMiLCIuLi9zcmMvSW50ZXJ2YWwuanMiLCIuLi9zcmMvSW5wdXRTdHJlYW0uanMiLCIuLi9zcmMvTWF0Y2hSZXN1bHQuanMiLCIuLi9zcmMvUG9zSW5mby5qcyIsIi4uL3NyYy9UcmFjZS5qcyIsIi4uL3NyYy9wZXhwcnMtYWxsb3dzU2tpcHBpbmdQcmVjZWRpbmdTcGFjZS5qcyIsIi4uL3NyYy9wZXhwcnMtYXNzZXJ0QWxsQXBwbGljYXRpb25zQXJlVmFsaWQuanMiLCIuLi9zcmMvcGV4cHJzLWFzc2VydENob2ljZXNIYXZlVW5pZm9ybUFyaXR5LmpzIiwiLi4vc3JjL3BleHBycy1hc3NlcnRJdGVyYXRlZEV4cHJzQXJlTm90TnVsbGFibGUuanMiLCIuLi9zcmMvbm9kZXMuanMiLCIuLi9zcmMvcGV4cHJzLWV2YWwuanMiLCIuLi9zcmMvcGV4cHJzLWdldEFyaXR5LmpzIiwiLi4vc3JjL3BleHBycy1vdXRwdXRSZWNpcGUuanMiLCIuLi9zcmMvcGV4cHJzLWludHJvZHVjZVBhcmFtcy5qcyIsIi4uL3NyYy9wZXhwcnMtaXNOdWxsYWJsZS5qcyIsIi4uL3NyYy9wZXhwcnMtc3Vic3RpdHV0ZVBhcmFtcy5qcyIsIi4uL3NyYy9wZXhwcnMtdG9Bcmd1bWVudE5hbWVMaXN0LmpzIiwiLi4vc3JjL3BleHBycy10b0Rpc3BsYXlTdHJpbmcuanMiLCIuLi9zcmMvRmFpbHVyZS5qcyIsIi4uL3NyYy9wZXhwcnMtdG9GYWlsdXJlLmpzIiwiLi4vc3JjL3BleHBycy10b1N0cmluZy5qcyIsIi4uL3NyYy9DYXNlSW5zZW5zaXRpdmVUZXJtaW5hbC5qcyIsIi4uL3NyYy9wZXhwcnMuanMiLCIuLi9zcmMvTWF0Y2hTdGF0ZS5qcyIsIi4uL3NyYy9NYXRjaGVyLmpzIiwiLi4vc3JjL1NlbWFudGljcy5qcyIsIi4uL3NyYy9HcmFtbWFyLmpzIiwiLi4vc3JjL0dyYW1tYXJEZWNsLmpzIiwiLi4vc3JjL0J1aWxkZXIuanMiLCIuLi9zcmMvbWFrZVJlY2lwZS5qcyIsImJ1aWx0LWluLXJ1bGVzLmpzIiwiLi4vc3JjL21haW4ta2VybmVsLmpzIiwib2htLWdyYW1tYXIuanMiLCIuLi9zcmMvYnVpbGRHcmFtbWFyLmpzIiwib3BlcmF0aW9ucy1hbmQtYXR0cmlidXRlcy5qcyIsIi4uL3NyYy9zZW1hbnRpY3NEZWZlcnJlZEluaXQuanMiLCIuLi9zcmMvZmluZEluZGVudGF0aW9uLmpzIiwiLi4vc3JjL0luZGVudGF0aW9uU2Vuc2l0aXZlLmpzIiwiLi4vc3JjL3ZlcnNpb24uanMiLCIuLi9zcmMvbWFpbi5qcyJdLCJzb3VyY2VzQ29udGVudCI6WyIvLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gUHJpdmF0ZSBTdHVmZlxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cblxuLy8gSGVscGVyc1xuXG5jb25zdCBlc2NhcGVTdHJpbmdGb3IgPSB7fTtcbmZvciAobGV0IGMgPSAwOyBjIDwgMTI4OyBjKyspIHtcbiAgZXNjYXBlU3RyaW5nRm9yW2NdID0gU3RyaW5nLmZyb21DaGFyQ29kZShjKTtcbn1cbmVzY2FwZVN0cmluZ0ZvcltcIidcIi5jaGFyQ29kZUF0KDApXSA9IFwiXFxcXCdcIjtcbmVzY2FwZVN0cmluZ0ZvclsnXCInLmNoYXJDb2RlQXQoMCldID0gJ1xcXFxcIic7XG5lc2NhcGVTdHJpbmdGb3JbJ1xcXFwnLmNoYXJDb2RlQXQoMCldID0gJ1xcXFxcXFxcJztcbmVzY2FwZVN0cmluZ0ZvclsnXFxiJy5jaGFyQ29kZUF0KDApXSA9ICdcXFxcYic7XG5lc2NhcGVTdHJpbmdGb3JbJ1xcZicuY2hhckNvZGVBdCgwKV0gPSAnXFxcXGYnO1xuZXNjYXBlU3RyaW5nRm9yWydcXG4nLmNoYXJDb2RlQXQoMCldID0gJ1xcXFxuJztcbmVzY2FwZVN0cmluZ0ZvclsnXFxyJy5jaGFyQ29kZUF0KDApXSA9ICdcXFxccic7XG5lc2NhcGVTdHJpbmdGb3JbJ1xcdCcuY2hhckNvZGVBdCgwKV0gPSAnXFxcXHQnO1xuZXNjYXBlU3RyaW5nRm9yWydcXHUwMDBiJy5jaGFyQ29kZUF0KDApXSA9ICdcXFxcdic7XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG4vLyBFeHBvcnRzXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuXG5leHBvcnQgZnVuY3Rpb24gYWJzdHJhY3Qob3B0TWV0aG9kTmFtZSkge1xuICBjb25zdCBtZXRob2ROYW1lID0gb3B0TWV0aG9kTmFtZSB8fCAnJztcbiAgcmV0dXJuIGZ1bmN0aW9uICgpIHtcbiAgICB0aHJvdyBuZXcgRXJyb3IoXG4gICAgICAndGhpcyBtZXRob2QgJyArXG4gICAgICAgIG1ldGhvZE5hbWUgK1xuICAgICAgICAnIGlzIGFic3RyYWN0ISAnICtcbiAgICAgICAgJyhpdCBoYXMgbm8gaW1wbGVtZW50YXRpb24gaW4gY2xhc3MgJyArXG4gICAgICAgIHRoaXMuY29uc3RydWN0b3IubmFtZSArXG4gICAgICAgICcpJ1xuICAgICk7XG4gIH07XG59XG5cbmV4cG9ydCBmdW5jdGlvbiBhc3NlcnQoY29uZCwgbWVzc2FnZSkge1xuICBpZiAoIWNvbmQpIHtcbiAgICB0aHJvdyBuZXcgRXJyb3IobWVzc2FnZSB8fCAnQXNzZXJ0aW9uIGZhaWxlZCcpO1xuICB9XG59XG5cbi8vIERlZmluZSBhIGxhemlseS1jb21wdXRlZCwgbm9uLWVudW1lcmFibGUgcHJvcGVydHkgbmFtZWQgYHByb3BOYW1lYFxuLy8gb24gdGhlIG9iamVjdCBgb2JqYC4gYGdldHRlckZuYCB3aWxsIGJlIGNhbGxlZCB0byBjb21wdXRlIHRoZSB2YWx1ZSB0aGVcbi8vIGZpcnN0IHRpbWUgdGhlIHByb3BlcnR5IGlzIGFjY2Vzc2VkLlxuZXhwb3J0IGZ1bmN0aW9uIGRlZmluZUxhenlQcm9wZXJ0eShvYmosIHByb3BOYW1lLCBnZXR0ZXJGbikge1xuICBsZXQgbWVtbztcbiAgT2JqZWN0LmRlZmluZVByb3BlcnR5KG9iaiwgcHJvcE5hbWUsIHtcbiAgICBnZXQoKSB7XG4gICAgICBpZiAoIW1lbW8pIHtcbiAgICAgICAgbWVtbyA9IGdldHRlckZuLmNhbGwodGhpcyk7XG4gICAgICB9XG4gICAgICByZXR1cm4gbWVtbztcbiAgICB9LFxuICB9KTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGNsb25lKG9iaikge1xuICBpZiAob2JqKSB7XG4gICAgcmV0dXJuIE9iamVjdC5hc3NpZ24oe30sIG9iaik7XG4gIH1cbiAgcmV0dXJuIG9iajtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIHJlcGVhdEZuKGZuLCBuKSB7XG4gIGNvbnN0IGFyciA9IFtdO1xuICB3aGlsZSAobi0tID4gMCkge1xuICAgIGFyci5wdXNoKGZuKCkpO1xuICB9XG4gIHJldHVybiBhcnI7XG59XG5cbmV4cG9ydCBmdW5jdGlvbiByZXBlYXRTdHIoc3RyLCBuKSB7XG4gIHJldHVybiBuZXcgQXJyYXkobiArIDEpLmpvaW4oc3RyKTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIHJlcGVhdCh4LCBuKSB7XG4gIHJldHVybiByZXBlYXRGbigoKSA9PiB4LCBuKTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGdldER1cGxpY2F0ZXMoYXJyYXkpIHtcbiAgY29uc3QgZHVwbGljYXRlcyA9IFtdO1xuICBmb3IgKGxldCBpZHggPSAwOyBpZHggPCBhcnJheS5sZW5ndGg7IGlkeCsrKSB7XG4gICAgY29uc3QgeCA9IGFycmF5W2lkeF07XG4gICAgaWYgKGFycmF5Lmxhc3RJbmRleE9mKHgpICE9PSBpZHggJiYgZHVwbGljYXRlcy5pbmRleE9mKHgpIDwgMCkge1xuICAgICAgZHVwbGljYXRlcy5wdXNoKHgpO1xuICAgIH1cbiAgfVxuICByZXR1cm4gZHVwbGljYXRlcztcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGNvcHlXaXRob3V0RHVwbGljYXRlcyhhcnJheSkge1xuICBjb25zdCBub0R1cGxpY2F0ZXMgPSBbXTtcbiAgYXJyYXkuZm9yRWFjaChlbnRyeSA9PiB7XG4gICAgaWYgKG5vRHVwbGljYXRlcy5pbmRleE9mKGVudHJ5KSA8IDApIHtcbiAgICAgIG5vRHVwbGljYXRlcy5wdXNoKGVudHJ5KTtcbiAgICB9XG4gIH0pO1xuICByZXR1cm4gbm9EdXBsaWNhdGVzO1xufVxuXG5leHBvcnQgZnVuY3Rpb24gaXNTeW50YWN0aWMocnVsZU5hbWUpIHtcbiAgY29uc3QgZmlyc3RDaGFyID0gcnVsZU5hbWVbMF07XG4gIHJldHVybiBmaXJzdENoYXIgPT09IGZpcnN0Q2hhci50b1VwcGVyQ2FzZSgpO1xufVxuXG5leHBvcnQgZnVuY3Rpb24gaXNMZXhpY2FsKHJ1bGVOYW1lKSB7XG4gIHJldHVybiAhaXNTeW50YWN0aWMocnVsZU5hbWUpO1xufVxuXG5leHBvcnQgZnVuY3Rpb24gcGFkTGVmdChzdHIsIGxlbiwgb3B0Q2hhcikge1xuICBjb25zdCBjaCA9IG9wdENoYXIgfHwgJyAnO1xuICBpZiAoc3RyLmxlbmd0aCA8IGxlbikge1xuICAgIHJldHVybiByZXBlYXRTdHIoY2gsIGxlbiAtIHN0ci5sZW5ndGgpICsgc3RyO1xuICB9XG4gIHJldHVybiBzdHI7XG59XG5cbi8vIFN0cmluZ0J1ZmZlclxuXG5leHBvcnQgZnVuY3Rpb24gU3RyaW5nQnVmZmVyKCkge1xuICB0aGlzLnN0cmluZ3MgPSBbXTtcbn1cblxuU3RyaW5nQnVmZmVyLnByb3RvdHlwZS5hcHBlbmQgPSBmdW5jdGlvbiAoc3RyKSB7XG4gIHRoaXMuc3RyaW5ncy5wdXNoKHN0cik7XG59O1xuXG5TdHJpbmdCdWZmZXIucHJvdG90eXBlLmNvbnRlbnRzID0gZnVuY3Rpb24gKCkge1xuICByZXR1cm4gdGhpcy5zdHJpbmdzLmpvaW4oJycpO1xufTtcblxuY29uc3QgZXNjYXBlVW5pY29kZSA9IHN0ciA9PiBTdHJpbmcuZnJvbUNvZGVQb2ludChwYXJzZUludChzdHIsIDE2KSk7XG5cbmV4cG9ydCBmdW5jdGlvbiB1bmVzY2FwZUNvZGVQb2ludChzKSB7XG4gIGlmIChzLmNoYXJBdCgwKSA9PT0gJ1xcXFwnKSB7XG4gICAgc3dpdGNoIChzLmNoYXJBdCgxKSkge1xuICAgICAgY2FzZSAnYic6XG4gICAgICAgIHJldHVybiAnXFxiJztcbiAgICAgIGNhc2UgJ2YnOlxuICAgICAgICByZXR1cm4gJ1xcZic7XG4gICAgICBjYXNlICduJzpcbiAgICAgICAgcmV0dXJuICdcXG4nO1xuICAgICAgY2FzZSAncic6XG4gICAgICAgIHJldHVybiAnXFxyJztcbiAgICAgIGNhc2UgJ3QnOlxuICAgICAgICByZXR1cm4gJ1xcdCc7XG4gICAgICBjYXNlICd2JzpcbiAgICAgICAgcmV0dXJuICdcXHYnO1xuICAgICAgY2FzZSAneCc6XG4gICAgICAgIHJldHVybiBlc2NhcGVVbmljb2RlKHMuc2xpY2UoMiwgNCkpO1xuICAgICAgY2FzZSAndSc6XG4gICAgICAgIHJldHVybiBzLmNoYXJBdCgyKSA9PT0gJ3snXG4gICAgICAgICAgPyBlc2NhcGVVbmljb2RlKHMuc2xpY2UoMywgLTEpKVxuICAgICAgICAgIDogZXNjYXBlVW5pY29kZShzLnNsaWNlKDIsIDYpKTtcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIHJldHVybiBzLmNoYXJBdCgxKTtcbiAgICB9XG4gIH0gZWxzZSB7XG4gICAgcmV0dXJuIHM7XG4gIH1cbn1cblxuLy8gSGVscGVyIGZvciBwcm9kdWNpbmcgYSBkZXNjcmlwdGlvbiBvZiBhbiB1bmtub3duIG9iamVjdCBpbiBhIHNhZmUgd2F5LlxuLy8gRXNwZWNpYWxseSB1c2VmdWwgZm9yIGVycm9yIG1lc3NhZ2VzIHdoZXJlIGFuIHVuZXhwZWN0ZWQgdHlwZSBvZiBvYmplY3Qgd2FzIGVuY291bnRlcmVkLlxuZXhwb3J0IGZ1bmN0aW9uIHVuZXhwZWN0ZWRPYmpUb1N0cmluZyhvYmopIHtcbiAgaWYgKG9iaiA9PSBudWxsKSB7XG4gICAgcmV0dXJuIFN0cmluZyhvYmopO1xuICB9XG4gIGNvbnN0IGJhc2VUb1N0cmluZyA9IE9iamVjdC5wcm90b3R5cGUudG9TdHJpbmcuY2FsbChvYmopO1xuICB0cnkge1xuICAgIGxldCB0eXBlTmFtZTtcbiAgICBpZiAob2JqLmNvbnN0cnVjdG9yICYmIG9iai5jb25zdHJ1Y3Rvci5uYW1lKSB7XG4gICAgICB0eXBlTmFtZSA9IG9iai5jb25zdHJ1Y3Rvci5uYW1lO1xuICAgIH0gZWxzZSBpZiAoYmFzZVRvU3RyaW5nLmluZGV4T2YoJ1tvYmplY3QgJykgPT09IDApIHtcbiAgICAgIHR5cGVOYW1lID0gYmFzZVRvU3RyaW5nLnNsaWNlKDgsIC0xKTsgLy8gRXh0cmFjdCBlLmcuIFwiQXJyYXlcIiBmcm9tIFwiW29iamVjdCBBcnJheV1cIi5cbiAgICB9IGVsc2Uge1xuICAgICAgdHlwZU5hbWUgPSB0eXBlb2Ygb2JqO1xuICAgIH1cbiAgICByZXR1cm4gdHlwZU5hbWUgKyAnOiAnICsgSlNPTi5zdHJpbmdpZnkoU3RyaW5nKG9iaikpO1xuICB9IGNhdGNoIHtcbiAgICByZXR1cm4gYmFzZVRvU3RyaW5nO1xuICB9XG59XG5cbmV4cG9ydCBmdW5jdGlvbiBjaGVja05vdE51bGwob2JqLCBtZXNzYWdlID0gJ3VuZXhwZWN0ZWQgbnVsbCB2YWx1ZScpIHtcbiAgaWYgKG9iaiA9PSBudWxsKSB7XG4gICAgdGhyb3cgbmV3IEVycm9yKG1lc3NhZ2UpO1xuICB9XG4gIHJldHVybiBvYmo7XG59XG4iLCIvLyBUaGUgZnVsbCBsaXN0IG9mIGNhdGVnb3JpZXMgZnJvbTpcbi8vIGh0dHBzOi8vd3d3LnVuaWNvZGUub3JnL1B1YmxpYy9VQ0QvbGF0ZXN0L3VjZC9leHRyYWN0ZWQvRGVyaXZlZEdlbmVyYWxDYXRlZ29yeS50eHQuXG5cbmNvbnN0IHRvUmVnRXhwID0gdmFsID0+IG5ldyBSZWdFeHAoU3RyaW5nLnJhd2BcXHB7JHt2YWx9fWAsICd1Jyk7XG5cbi8qXG4gIGdyZXAgLXYgJ14jJyBEZXJpdmVkR2VuZXJhbENhdGVnb3J5LnR4dCBcXFxuICAgIHwgY3V0IC1kJzsnIC1mMiBcXFxuICAgIHwgYXdrICdORntwcmludCAkMX0nIFxcXG4gICAgfCBzb3J0IC11IFxcXG4gICAgfCBhd2sgJ3twcmludGYgXCJcXHgyNyVzXFx4MjcsXFxuXCIsJDF9J1xuICovXG5cbmV4cG9ydCBjb25zdCBVbmljb2RlQ2F0ZWdvcmllcyA9IE9iamVjdC5mcm9tRW50cmllcyhcbiAgW1xuICAgICdDYycsXG4gICAgJ0NmJyxcbiAgICAnQ24nLFxuICAgICdDbycsXG4gICAgJ0NzJyxcbiAgICAnTGwnLFxuICAgICdMbScsXG4gICAgJ0xvJyxcbiAgICAnTHQnLFxuICAgICdMdScsXG4gICAgJ01jJyxcbiAgICAnTWUnLFxuICAgICdNbicsXG4gICAgJ05kJyxcbiAgICAnTmwnLFxuICAgICdObycsXG4gICAgJ1BjJyxcbiAgICAnUGQnLFxuICAgICdQZScsXG4gICAgJ1BmJyxcbiAgICAnUGknLFxuICAgICdQbycsXG4gICAgJ1BzJyxcbiAgICAnU2MnLFxuICAgICdTaycsXG4gICAgJ1NtJyxcbiAgICAnU28nLFxuICAgICdabCcsXG4gICAgJ1pwJyxcbiAgICAnWnMnLFxuICBdLm1hcChjYXQgPT4gW2NhdCwgdG9SZWdFeHAoY2F0KV0pXG4pO1xuVW5pY29kZUNhdGVnb3JpZXNbJ0x0bW8nXSA9IC9cXHB7THR9fFxccHtMbX18XFxwe0xvfS91O1xuXG4vLyBXZSBvbmx5IHN1cHBvcnQgYSBmZXcgb2YgdGhlc2UgZm9yIG5vdywgYnV0IGNvdWxkIGFkZCBtb3JlIGxhdGVyLlxuLy8gU2VlIGh0dHBzOi8vd3d3LnVuaWNvZGUub3JnL1B1YmxpYy9VQ0QvbGF0ZXN0L3VjZC9Qcm9wZXJ0eUFsaWFzZXMudHh0XG5leHBvcnQgY29uc3QgVW5pY29kZUJpbmFyeVByb3BlcnRpZXMgPSBPYmplY3QuZnJvbUVudHJpZXMoXG4gIFsnWElEX1N0YXJ0JywgJ1hJRF9Db250aW51ZScsICdXaGl0ZV9TcGFjZSddLm1hcChwcm9wID0+IFtwcm9wLCB0b1JlZ0V4cChwcm9wKV0pXG4pO1xuIiwiaW1wb3J0IHtVbmljb2RlQmluYXJ5UHJvcGVydGllcywgVW5pY29kZUNhdGVnb3JpZXN9IGZyb20gJy4vdW5pY29kZS5qcyc7XG5pbXBvcnQgKiBhcyBjb21tb24gZnJvbSAnLi9jb21tb24uanMnO1xuXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gUHJpdmF0ZSBzdHVmZlxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cblxuLy8gR2VuZXJhbCBzdHVmZlxuXG5leHBvcnQgY2xhc3MgUEV4cHIge1xuICBjb25zdHJ1Y3RvcigpIHtcbiAgICBpZiAodGhpcy5jb25zdHJ1Y3RvciA9PT0gUEV4cHIpIHtcbiAgICAgIHRocm93IG5ldyBFcnJvcihcIlBFeHByIGNhbm5vdCBiZSBpbnN0YW50aWF0ZWQgLS0gaXQncyBhYnN0cmFjdFwiKTtcbiAgICB9XG4gIH1cblxuICAvLyBTZXQgdGhlIGBzb3VyY2VgIHByb3BlcnR5IHRvIHRoZSBpbnRlcnZhbCBjb250YWluaW5nIHRoZSBzb3VyY2UgZm9yIHRoaXMgZXhwcmVzc2lvbi5cbiAgd2l0aFNvdXJjZShpbnRlcnZhbCkge1xuICAgIGlmIChpbnRlcnZhbCkge1xuICAgICAgdGhpcy5zb3VyY2UgPSBpbnRlcnZhbC50cmltbWVkKCk7XG4gICAgfVxuICAgIHJldHVybiB0aGlzO1xuICB9XG59XG5cbi8vIEFueVxuXG5leHBvcnQgY29uc3QgYW55ID0gT2JqZWN0LmNyZWF0ZShQRXhwci5wcm90b3R5cGUpO1xuXG4vLyBFbmRcblxuZXhwb3J0IGNvbnN0IGVuZCA9IE9iamVjdC5jcmVhdGUoUEV4cHIucHJvdG90eXBlKTtcblxuLy8gVGVybWluYWxzXG5cbmV4cG9ydCBjbGFzcyBUZXJtaW5hbCBleHRlbmRzIFBFeHByIHtcbiAgY29uc3RydWN0b3Iob2JqKSB7XG4gICAgc3VwZXIoKTtcbiAgICB0aGlzLm9iaiA9IG9iajtcbiAgfVxufVxuXG4vLyBSYW5nZXNcblxuZXhwb3J0IGNsYXNzIFJhbmdlIGV4dGVuZHMgUEV4cHIge1xuICBjb25zdHJ1Y3Rvcihmcm9tLCB0bykge1xuICAgIHN1cGVyKCk7XG4gICAgdGhpcy5mcm9tID0gZnJvbTtcbiAgICB0aGlzLnRvID0gdG87XG4gICAgLy8gSWYgZWl0aGVyIGBmcm9tYCBvciBgdG9gIGlzIG1hZGUgdXAgb2YgbXVsdGlwbGUgY29kZSB1bml0cywgdGhlblxuICAgIC8vIHRoZSByYW5nZSBzaG91bGQgY29uc3VtZSBhIGZ1bGwgY29kZSBwb2ludCwgbm90IGEgc2luZ2xlIGNvZGUgdW5pdC5cbiAgICB0aGlzLm1hdGNoQ29kZVBvaW50ID0gZnJvbS5sZW5ndGggPiAxIHx8IHRvLmxlbmd0aCA+IDE7XG4gIH1cbn1cblxuLy8gUGFyYW1ldGVyc1xuXG5leHBvcnQgY2xhc3MgUGFyYW0gZXh0ZW5kcyBQRXhwciB7XG4gIGNvbnN0cnVjdG9yKGluZGV4KSB7XG4gICAgc3VwZXIoKTtcbiAgICB0aGlzLmluZGV4ID0gaW5kZXg7XG4gIH1cbn1cblxuLy8gQWx0ZXJuYXRpb25cblxuZXhwb3J0IGNsYXNzIEFsdCBleHRlbmRzIFBFeHByIHtcbiAgY29uc3RydWN0b3IodGVybXMpIHtcbiAgICBzdXBlcigpO1xuICAgIHRoaXMudGVybXMgPSB0ZXJtcztcbiAgfVxufVxuXG4vLyBFeHRlbmQgaXMgYW4gaW1wbGVtZW50YXRpb24gZGV0YWlsIG9mIHJ1bGUgZXh0ZW5zaW9uXG5cbmV4cG9ydCBjbGFzcyBFeHRlbmQgZXh0ZW5kcyBBbHQge1xuICBjb25zdHJ1Y3RvcihzdXBlckdyYW1tYXIsIG5hbWUsIGJvZHkpIHtcbiAgICBjb25zdCBvcmlnQm9keSA9IHN1cGVyR3JhbW1hci5ydWxlc1tuYW1lXS5ib2R5O1xuICAgIHN1cGVyKFtib2R5LCBvcmlnQm9keV0pO1xuXG4gICAgdGhpcy5zdXBlckdyYW1tYXIgPSBzdXBlckdyYW1tYXI7XG4gICAgdGhpcy5uYW1lID0gbmFtZTtcbiAgICB0aGlzLmJvZHkgPSBib2R5O1xuICB9XG59XG5cbi8vIFNwbGljZSBpcyBhbiBpbXBsZW1lbnRhdGlvbiBkZXRhaWwgb2YgcnVsZSBvdmVycmlkaW5nIHdpdGggdGhlIGAuLi5gIG9wZXJhdG9yLlxuZXhwb3J0IGNsYXNzIFNwbGljZSBleHRlbmRzIEFsdCB7XG4gIGNvbnN0cnVjdG9yKHN1cGVyR3JhbW1hciwgcnVsZU5hbWUsIGJlZm9yZVRlcm1zLCBhZnRlclRlcm1zKSB7XG4gICAgY29uc3Qgb3JpZ0JvZHkgPSBzdXBlckdyYW1tYXIucnVsZXNbcnVsZU5hbWVdLmJvZHk7XG4gICAgc3VwZXIoWy4uLmJlZm9yZVRlcm1zLCBvcmlnQm9keSwgLi4uYWZ0ZXJUZXJtc10pO1xuXG4gICAgdGhpcy5zdXBlckdyYW1tYXIgPSBzdXBlckdyYW1tYXI7XG4gICAgdGhpcy5ydWxlTmFtZSA9IHJ1bGVOYW1lO1xuICAgIHRoaXMuZXhwYW5zaW9uUG9zID0gYmVmb3JlVGVybXMubGVuZ3RoO1xuICB9XG59XG5cbi8vIFNlcXVlbmNlc1xuXG5leHBvcnQgY2xhc3MgU2VxIGV4dGVuZHMgUEV4cHIge1xuICBjb25zdHJ1Y3RvcihmYWN0b3JzKSB7XG4gICAgc3VwZXIoKTtcbiAgICB0aGlzLmZhY3RvcnMgPSBmYWN0b3JzO1xuICB9XG59XG5cbi8vIEl0ZXJhdG9ycyBhbmQgb3B0aW9uYWxzXG5cbmV4cG9ydCBjbGFzcyBJdGVyIGV4dGVuZHMgUEV4cHIge1xuICBjb25zdHJ1Y3RvcihleHByKSB7XG4gICAgc3VwZXIoKTtcbiAgICB0aGlzLmV4cHIgPSBleHByO1xuICB9XG59XG5cbmV4cG9ydCBjbGFzcyBTdGFyIGV4dGVuZHMgSXRlciB7fVxuZXhwb3J0IGNsYXNzIFBsdXMgZXh0ZW5kcyBJdGVyIHt9XG5leHBvcnQgY2xhc3MgT3B0IGV4dGVuZHMgSXRlciB7fVxuXG5TdGFyLnByb3RvdHlwZS5vcGVyYXRvciA9ICcqJztcblBsdXMucHJvdG90eXBlLm9wZXJhdG9yID0gJysnO1xuT3B0LnByb3RvdHlwZS5vcGVyYXRvciA9ICc/JztcblxuU3Rhci5wcm90b3R5cGUubWluTnVtTWF0Y2hlcyA9IDA7XG5QbHVzLnByb3RvdHlwZS5taW5OdW1NYXRjaGVzID0gMTtcbk9wdC5wcm90b3R5cGUubWluTnVtTWF0Y2hlcyA9IDA7XG5cblN0YXIucHJvdG90eXBlLm1heE51bU1hdGNoZXMgPSBOdW1iZXIuUE9TSVRJVkVfSU5GSU5JVFk7XG5QbHVzLnByb3RvdHlwZS5tYXhOdW1NYXRjaGVzID0gTnVtYmVyLlBPU0lUSVZFX0lORklOSVRZO1xuT3B0LnByb3RvdHlwZS5tYXhOdW1NYXRjaGVzID0gMTtcblxuLy8gUHJlZGljYXRlc1xuXG5leHBvcnQgY2xhc3MgTm90IGV4dGVuZHMgUEV4cHIge1xuICBjb25zdHJ1Y3RvcihleHByKSB7XG4gICAgc3VwZXIoKTtcbiAgICB0aGlzLmV4cHIgPSBleHByO1xuICB9XG59XG5cbmV4cG9ydCBjbGFzcyBMb29rYWhlYWQgZXh0ZW5kcyBQRXhwciB7XG4gIGNvbnN0cnVjdG9yKGV4cHIpIHtcbiAgICBzdXBlcigpO1xuICAgIHRoaXMuZXhwciA9IGV4cHI7XG4gIH1cbn1cblxuLy8gXCJMZXhpZmljYXRpb25cIlxuXG5leHBvcnQgY2xhc3MgTGV4IGV4dGVuZHMgUEV4cHIge1xuICBjb25zdHJ1Y3RvcihleHByKSB7XG4gICAgc3VwZXIoKTtcbiAgICB0aGlzLmV4cHIgPSBleHByO1xuICB9XG59XG5cbi8vIFJ1bGUgYXBwbGljYXRpb25cblxuZXhwb3J0IGNsYXNzIEFwcGx5IGV4dGVuZHMgUEV4cHIge1xuICBjb25zdHJ1Y3RvcihydWxlTmFtZSwgYXJncyA9IFtdKSB7XG4gICAgc3VwZXIoKTtcbiAgICB0aGlzLnJ1bGVOYW1lID0gcnVsZU5hbWU7XG4gICAgdGhpcy5hcmdzID0gYXJncztcbiAgfVxuXG4gIGlzU3ludGFjdGljKCkge1xuICAgIHJldHVybiBjb21tb24uaXNTeW50YWN0aWModGhpcy5ydWxlTmFtZSk7XG4gIH1cblxuICAvLyBUaGlzIG1ldGhvZCBqdXN0IGNhY2hlcyB0aGUgcmVzdWx0IG9mIGB0aGlzLnRvU3RyaW5nKClgIGluIGEgbm9uLWVudW1lcmFibGUgcHJvcGVydHkuXG4gIHRvTWVtb0tleSgpIHtcbiAgICBpZiAoIXRoaXMuX21lbW9LZXkpIHtcbiAgICAgIE9iamVjdC5kZWZpbmVQcm9wZXJ0eSh0aGlzLCAnX21lbW9LZXknLCB7dmFsdWU6IHRoaXMudG9TdHJpbmcoKX0pO1xuICAgIH1cbiAgICByZXR1cm4gdGhpcy5fbWVtb0tleTtcbiAgfVxufVxuXG4vLyBVbmljb2RlIGNoYXJhY3RlclxuXG5leHBvcnQgY2xhc3MgVW5pY29kZUNoYXIgZXh0ZW5kcyBQRXhwciB7XG4gIGNvbnN0cnVjdG9yKGNhdGVnb3J5T3JQcm9wKSB7XG4gICAgc3VwZXIoKTtcbiAgICB0aGlzLmNhdGVnb3J5T3JQcm9wID0gY2F0ZWdvcnlPclByb3A7XG4gICAgaWYgKGNhdGVnb3J5T3JQcm9wIGluIFVuaWNvZGVDYXRlZ29yaWVzKSB7XG4gICAgICB0aGlzLnBhdHRlcm4gPSBVbmljb2RlQ2F0ZWdvcmllc1tjYXRlZ29yeU9yUHJvcF07XG4gICAgfSBlbHNlIGlmIChjYXRlZ29yeU9yUHJvcCBpbiBVbmljb2RlQmluYXJ5UHJvcGVydGllcykge1xuICAgICAgdGhpcy5wYXR0ZXJuID0gVW5pY29kZUJpbmFyeVByb3BlcnRpZXNbY2F0ZWdvcnlPclByb3BdO1xuICAgIH0gZWxzZSB7XG4gICAgICB0aHJvdyBuZXcgRXJyb3IoXG4gICAgICAgIGBJbnZhbGlkIFVuaWNvZGUgY2F0ZWdvcnkgb3IgcHJvcGVydHkgbmFtZTogJHtKU09OLnN0cmluZ2lmeShjYXRlZ29yeU9yUHJvcCl9YFxuICAgICAgKTtcbiAgICB9XG4gIH1cbn1cbiIsImltcG9ydCB7YXNzZXJ0fSBmcm9tICcuL2NvbW1vbi5qcyc7XG5pbXBvcnQgKiBhcyBwZXhwcnMgZnJvbSAnLi9wZXhwcnMtbWFpbi5qcyc7XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG4vLyBQcml2YXRlIHN0dWZmXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuXG5leHBvcnQgZnVuY3Rpb24gY3JlYXRlRXJyb3IobWVzc2FnZSwgb3B0SW50ZXJ2YWwpIHtcbiAgbGV0IGU7XG4gIGlmIChvcHRJbnRlcnZhbCkge1xuICAgIGUgPSBuZXcgRXJyb3Iob3B0SW50ZXJ2YWwuZ2V0TGluZUFuZENvbHVtbk1lc3NhZ2UoKSArIG1lc3NhZ2UpO1xuICAgIGUuc2hvcnRNZXNzYWdlID0gbWVzc2FnZTtcbiAgICBlLmludGVydmFsID0gb3B0SW50ZXJ2YWw7XG4gIH0gZWxzZSB7XG4gICAgZSA9IG5ldyBFcnJvcihtZXNzYWdlKTtcbiAgfVxuICByZXR1cm4gZTtcbn1cblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0gZXJyb3JzIGFib3V0IGludGVydmFscyAtLS0tLS0tLS0tLS0tLS0tLVxuXG5leHBvcnQgZnVuY3Rpb24gaW50ZXJ2YWxTb3VyY2VzRG9udE1hdGNoKCkge1xuICByZXR1cm4gY3JlYXRlRXJyb3IoXCJJbnRlcnZhbCBzb3VyY2VzIGRvbid0IG1hdGNoXCIpO1xufVxuXG4vLyAtLS0tLS0tLS0tLS0tLS0tLSBlcnJvcnMgYWJvdXQgZ3JhbW1hcnMgLS0tLS0tLS0tLS0tLS0tLS1cblxuLy8gR3JhbW1hciBzeW50YXggZXJyb3JcblxuZXhwb3J0IGZ1bmN0aW9uIGdyYW1tYXJTeW50YXhFcnJvcihtYXRjaEZhaWx1cmUpIHtcbiAgY29uc3QgZSA9IG5ldyBFcnJvcigpO1xuICBPYmplY3QuZGVmaW5lUHJvcGVydHkoZSwgJ21lc3NhZ2UnLCB7XG4gICAgZW51bWVyYWJsZTogdHJ1ZSxcbiAgICBnZXQoKSB7XG4gICAgICByZXR1cm4gbWF0Y2hGYWlsdXJlLm1lc3NhZ2U7XG4gICAgfSxcbiAgfSk7XG4gIE9iamVjdC5kZWZpbmVQcm9wZXJ0eShlLCAnc2hvcnRNZXNzYWdlJywge1xuICAgIGVudW1lcmFibGU6IHRydWUsXG4gICAgZ2V0KCkge1xuICAgICAgcmV0dXJuICdFeHBlY3RlZCAnICsgbWF0Y2hGYWlsdXJlLmdldEV4cGVjdGVkVGV4dCgpO1xuICAgIH0sXG4gIH0pO1xuICBlLmludGVydmFsID0gbWF0Y2hGYWlsdXJlLmdldEludGVydmFsKCk7XG4gIHJldHVybiBlO1xufVxuXG4vLyBVbmRlY2xhcmVkIGdyYW1tYXJcblxuZXhwb3J0IGZ1bmN0aW9uIHVuZGVjbGFyZWRHcmFtbWFyKGdyYW1tYXJOYW1lLCBuYW1lc3BhY2UsIGludGVydmFsKSB7XG4gIGNvbnN0IG1lc3NhZ2UgPSBuYW1lc3BhY2VcbiAgICA/IGBHcmFtbWFyICR7Z3JhbW1hck5hbWV9IGlzIG5vdCBkZWNsYXJlZCBpbiBuYW1lc3BhY2UgJyR7bmFtZXNwYWNlfSdgXG4gICAgOiAnVW5kZWNsYXJlZCBncmFtbWFyICcgKyBncmFtbWFyTmFtZTtcbiAgcmV0dXJuIGNyZWF0ZUVycm9yKG1lc3NhZ2UsIGludGVydmFsKTtcbn1cblxuLy8gRHVwbGljYXRlIGdyYW1tYXIgZGVjbGFyYXRpb25cblxuZXhwb3J0IGZ1bmN0aW9uIGR1cGxpY2F0ZUdyYW1tYXJEZWNsYXJhdGlvbihncmFtbWFyLCBuYW1lc3BhY2UpIHtcbiAgcmV0dXJuIGNyZWF0ZUVycm9yKCdHcmFtbWFyICcgKyBncmFtbWFyLm5hbWUgKyAnIGlzIGFscmVhZHkgZGVjbGFyZWQgaW4gdGhpcyBuYW1lc3BhY2UnKTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGdyYW1tYXJEb2VzTm90U3VwcG9ydEluY3JlbWVudGFsUGFyc2luZyhncmFtbWFyKSB7XG4gIHJldHVybiBjcmVhdGVFcnJvcihgR3JhbW1hciAnJHtncmFtbWFyLm5hbWV9JyBkb2VzIG5vdCBzdXBwb3J0IGluY3JlbWVudGFsIHBhcnNpbmdgKTtcbn1cblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0gcnVsZXMgLS0tLS0tLS0tLS0tLS0tLS1cblxuLy8gVW5kZWNsYXJlZCBydWxlXG5cbmV4cG9ydCBmdW5jdGlvbiB1bmRlY2xhcmVkUnVsZShydWxlTmFtZSwgZ3JhbW1hck5hbWUsIG9wdEludGVydmFsKSB7XG4gIHJldHVybiBjcmVhdGVFcnJvcihcbiAgICAnUnVsZSAnICsgcnVsZU5hbWUgKyAnIGlzIG5vdCBkZWNsYXJlZCBpbiBncmFtbWFyICcgKyBncmFtbWFyTmFtZSxcbiAgICBvcHRJbnRlcnZhbFxuICApO1xufVxuXG4vLyBDYW5ub3Qgb3ZlcnJpZGUgdW5kZWNsYXJlZCBydWxlXG5cbmV4cG9ydCBmdW5jdGlvbiBjYW5ub3RPdmVycmlkZVVuZGVjbGFyZWRSdWxlKHJ1bGVOYW1lLCBncmFtbWFyTmFtZSwgb3B0U291cmNlKSB7XG4gIHJldHVybiBjcmVhdGVFcnJvcihcbiAgICAnQ2Fubm90IG92ZXJyaWRlIHJ1bGUgJyArIHJ1bGVOYW1lICsgJyBiZWNhdXNlIGl0IGlzIG5vdCBkZWNsYXJlZCBpbiAnICsgZ3JhbW1hck5hbWUsXG4gICAgb3B0U291cmNlXG4gICk7XG59XG5cbi8vIENhbm5vdCBleHRlbmQgdW5kZWNsYXJlZCBydWxlXG5cbmV4cG9ydCBmdW5jdGlvbiBjYW5ub3RFeHRlbmRVbmRlY2xhcmVkUnVsZShydWxlTmFtZSwgZ3JhbW1hck5hbWUsIG9wdFNvdXJjZSkge1xuICByZXR1cm4gY3JlYXRlRXJyb3IoXG4gICAgJ0Nhbm5vdCBleHRlbmQgcnVsZSAnICsgcnVsZU5hbWUgKyAnIGJlY2F1c2UgaXQgaXMgbm90IGRlY2xhcmVkIGluICcgKyBncmFtbWFyTmFtZSxcbiAgICBvcHRTb3VyY2VcbiAgKTtcbn1cblxuLy8gRHVwbGljYXRlIHJ1bGUgZGVjbGFyYXRpb25cblxuZXhwb3J0IGZ1bmN0aW9uIGR1cGxpY2F0ZVJ1bGVEZWNsYXJhdGlvbihydWxlTmFtZSwgZ3JhbW1hck5hbWUsIGRlY2xHcmFtbWFyTmFtZSwgb3B0U291cmNlKSB7XG4gIGxldCBtZXNzYWdlID1cbiAgICBcIkR1cGxpY2F0ZSBkZWNsYXJhdGlvbiBmb3IgcnVsZSAnXCIgKyBydWxlTmFtZSArIFwiJyBpbiBncmFtbWFyICdcIiArIGdyYW1tYXJOYW1lICsgXCInXCI7XG4gIGlmIChncmFtbWFyTmFtZSAhPT0gZGVjbEdyYW1tYXJOYW1lKSB7XG4gICAgbWVzc2FnZSArPSBcIiAob3JpZ2luYWxseSBkZWNsYXJlZCBpbiAnXCIgKyBkZWNsR3JhbW1hck5hbWUgKyBcIicpXCI7XG4gIH1cbiAgcmV0dXJuIGNyZWF0ZUVycm9yKG1lc3NhZ2UsIG9wdFNvdXJjZSk7XG59XG5cbi8vIFdyb25nIG51bWJlciBvZiBwYXJhbWV0ZXJzXG5cbmV4cG9ydCBmdW5jdGlvbiB3cm9uZ051bWJlck9mUGFyYW1ldGVycyhydWxlTmFtZSwgZXhwZWN0ZWQsIGFjdHVhbCwgc291cmNlKSB7XG4gIHJldHVybiBjcmVhdGVFcnJvcihcbiAgICAnV3JvbmcgbnVtYmVyIG9mIHBhcmFtZXRlcnMgZm9yIHJ1bGUgJyArXG4gICAgICBydWxlTmFtZSArXG4gICAgICAnIChleHBlY3RlZCAnICtcbiAgICAgIGV4cGVjdGVkICtcbiAgICAgICcsIGdvdCAnICtcbiAgICAgIGFjdHVhbCArXG4gICAgICAnKScsXG4gICAgc291cmNlXG4gICk7XG59XG5cbi8vIFdyb25nIG51bWJlciBvZiBhcmd1bWVudHNcblxuZXhwb3J0IGZ1bmN0aW9uIHdyb25nTnVtYmVyT2ZBcmd1bWVudHMocnVsZU5hbWUsIGV4cGVjdGVkLCBhY3R1YWwsIGV4cHIpIHtcbiAgcmV0dXJuIGNyZWF0ZUVycm9yKFxuICAgICdXcm9uZyBudW1iZXIgb2YgYXJndW1lbnRzIGZvciBydWxlICcgK1xuICAgICAgcnVsZU5hbWUgK1xuICAgICAgJyAoZXhwZWN0ZWQgJyArXG4gICAgICBleHBlY3RlZCArXG4gICAgICAnLCBnb3QgJyArXG4gICAgICBhY3R1YWwgK1xuICAgICAgJyknLFxuICAgIGV4cHJcbiAgKTtcbn1cblxuLy8gRHVwbGljYXRlIHBhcmFtZXRlciBuYW1lc1xuXG5leHBvcnQgZnVuY3Rpb24gZHVwbGljYXRlUGFyYW1ldGVyTmFtZXMocnVsZU5hbWUsIGR1cGxpY2F0ZXMsIHNvdXJjZSkge1xuICByZXR1cm4gY3JlYXRlRXJyb3IoXG4gICAgJ0R1cGxpY2F0ZSBwYXJhbWV0ZXIgbmFtZXMgaW4gcnVsZSAnICsgcnVsZU5hbWUgKyAnOiAnICsgZHVwbGljYXRlcy5qb2luKCcsICcpLFxuICAgIHNvdXJjZVxuICApO1xufVxuXG4vLyBJbnZhbGlkIHBhcmFtZXRlciBleHByZXNzaW9uXG5cbmV4cG9ydCBmdW5jdGlvbiBpbnZhbGlkUGFyYW1ldGVyKHJ1bGVOYW1lLCBleHByKSB7XG4gIHJldHVybiBjcmVhdGVFcnJvcihcbiAgICAnSW52YWxpZCBwYXJhbWV0ZXIgdG8gcnVsZSAnICtcbiAgICAgIHJ1bGVOYW1lICtcbiAgICAgICc6ICcgK1xuICAgICAgZXhwciArXG4gICAgICAnIGhhcyBhcml0eSAnICtcbiAgICAgIGV4cHIuZ2V0QXJpdHkoKSArXG4gICAgICAnLCBidXQgcGFyYW1ldGVyIGV4cHJlc3Npb25zIG11c3QgaGF2ZSBhcml0eSAxJyxcbiAgICBleHByLnNvdXJjZVxuICApO1xufVxuXG4vLyBBcHBsaWNhdGlvbiBvZiBzeW50YWN0aWMgcnVsZSBmcm9tIGxleGljYWwgcnVsZVxuXG5jb25zdCBzeW50YWN0aWNWc0xleGljYWxOb3RlID1cbiAgJ05PVEU6IEEgX3N5bnRhY3RpYyBydWxlXyBpcyBhIHJ1bGUgd2hvc2UgbmFtZSBiZWdpbnMgd2l0aCBhIGNhcGl0YWwgbGV0dGVyLiAnICtcbiAgJ1NlZSBodHRwczovL29obWpzLm9yZy9kL3N2bCBmb3IgbW9yZSBkZXRhaWxzLic7XG5cbmV4cG9ydCBmdW5jdGlvbiBhcHBsaWNhdGlvbk9mU3ludGFjdGljUnVsZUZyb21MZXhpY2FsQ29udGV4dChydWxlTmFtZSwgYXBwbHlFeHByKSB7XG4gIHJldHVybiBjcmVhdGVFcnJvcihcbiAgICAnQ2Fubm90IGFwcGx5IHN5bnRhY3RpYyBydWxlICcgKyBydWxlTmFtZSArICcgZnJvbSBoZXJlIChpbnNpZGUgYSBsZXhpY2FsIGNvbnRleHQpJyxcbiAgICBhcHBseUV4cHIuc291cmNlXG4gICk7XG59XG5cbi8vIExleGljYWwgcnVsZSBhcHBsaWNhdGlvbiB1c2VkIHdpdGggYXBwbHlTeW50YWN0aWNcblxuZXhwb3J0IGZ1bmN0aW9uIGFwcGx5U3ludGFjdGljV2l0aExleGljYWxSdWxlQXBwbGljYXRpb24oYXBwbHlFeHByKSB7XG4gIGNvbnN0IHtydWxlTmFtZX0gPSBhcHBseUV4cHI7XG4gIHJldHVybiBjcmVhdGVFcnJvcihcbiAgICBgYXBwbHlTeW50YWN0aWMgaXMgZm9yIHN5bnRhY3RpYyBydWxlcywgYnV0ICcke3J1bGVOYW1lfScgaXMgYSBsZXhpY2FsIHJ1bGUuIGAgK1xuICAgICAgc3ludGFjdGljVnNMZXhpY2FsTm90ZSxcbiAgICBhcHBseUV4cHIuc291cmNlXG4gICk7XG59XG5cbi8vIEFwcGxpY2F0aW9uIG9mIGFwcGx5U3ludGFjdGljIGluIGEgc3ludGFjdGljIGNvbnRleHRcblxuZXhwb3J0IGZ1bmN0aW9uIHVubmVjZXNzYXJ5RXhwZXJpbWVudGFsQXBwbHlTeW50YWN0aWMoYXBwbHlFeHByKSB7XG4gIHJldHVybiBjcmVhdGVFcnJvcihcbiAgICAnYXBwbHlTeW50YWN0aWMgaXMgbm90IHJlcXVpcmVkIGhlcmUgKGluIGEgc3ludGFjdGljIGNvbnRleHQpJyxcbiAgICBhcHBseUV4cHIuc291cmNlXG4gICk7XG59XG5cbi8vIEluY29ycmVjdCBhcmd1bWVudCB0eXBlXG5cbmV4cG9ydCBmdW5jdGlvbiBpbmNvcnJlY3RBcmd1bWVudFR5cGUoZXhwZWN0ZWRUeXBlLCBleHByKSB7XG4gIHJldHVybiBjcmVhdGVFcnJvcignSW5jb3JyZWN0IGFyZ3VtZW50IHR5cGU6IGV4cGVjdGVkICcgKyBleHBlY3RlZFR5cGUsIGV4cHIuc291cmNlKTtcbn1cblxuLy8gTXVsdGlwbGUgaW5zdGFuY2VzIG9mIHRoZSBzdXBlci1zcGxpY2Ugb3BlcmF0b3IgKGAuLi5gKSBpbiB0aGUgcnVsZSBib2R5LlxuXG5leHBvcnQgZnVuY3Rpb24gbXVsdGlwbGVTdXBlclNwbGljZXMoZXhwcikge1xuICByZXR1cm4gY3JlYXRlRXJyb3IoXCInLi4uJyBjYW4gYXBwZWFyIGF0IG1vc3Qgb25jZSBpbiBhIHJ1bGUgYm9keVwiLCBleHByLnNvdXJjZSk7XG59XG5cbi8vIFVuaWNvZGUgY29kZSBwb2ludCBlc2NhcGVzXG5cbmV4cG9ydCBmdW5jdGlvbiBpbnZhbGlkQ29kZVBvaW50KGFwcGx5V3JhcHBlcikge1xuICBjb25zdCBub2RlID0gYXBwbHlXcmFwcGVyLl9ub2RlO1xuICBhc3NlcnQobm9kZSAmJiBub2RlLmlzTm9udGVybWluYWwoKSAmJiBub2RlLmN0b3JOYW1lID09PSAnZXNjYXBlQ2hhcl91bmljb2RlQ29kZVBvaW50Jyk7XG5cbiAgLy8gR2V0IGFuIGludGVydmFsIHRoYXQgY292ZXJzIGFsbCBvZiB0aGUgaGV4IGRpZ2l0cy5cbiAgY29uc3QgZGlnaXRJbnRlcnZhbHMgPSBhcHBseVdyYXBwZXIuY2hpbGRyZW4uc2xpY2UoMSwgLTEpLm1hcChkID0+IGQuc291cmNlKTtcbiAgY29uc3QgZnVsbEludGVydmFsID0gZGlnaXRJbnRlcnZhbHNbMF0uY292ZXJhZ2VXaXRoKC4uLmRpZ2l0SW50ZXJ2YWxzLnNsaWNlKDEpKTtcbiAgcmV0dXJuIGNyZWF0ZUVycm9yKFxuICAgIGBVKyR7ZnVsbEludGVydmFsLmNvbnRlbnRzfSBpcyBub3QgYSB2YWxpZCBVbmljb2RlIGNvZGUgcG9pbnRgLFxuICAgIGZ1bGxJbnRlcnZhbFxuICApO1xufVxuXG4vLyAtLS0tLS0tLS0tLS0tLS0tLSBLbGVlbmUgb3BlcmF0b3JzIC0tLS0tLS0tLS0tLS0tLS0tXG5cbmV4cG9ydCBmdW5jdGlvbiBrbGVlbmVFeHBySGFzTnVsbGFibGVPcGVyYW5kKGtsZWVuZUV4cHIsIGFwcGxpY2F0aW9uU3RhY2spIHtcbiAgY29uc3QgYWN0dWFscyA9XG4gICAgYXBwbGljYXRpb25TdGFjay5sZW5ndGggPiAwID8gYXBwbGljYXRpb25TdGFja1thcHBsaWNhdGlvblN0YWNrLmxlbmd0aCAtIDFdLmFyZ3MgOiBbXTtcbiAgY29uc3QgZXhwciA9IGtsZWVuZUV4cHIuZXhwci5zdWJzdGl0dXRlUGFyYW1zKGFjdHVhbHMpO1xuICBsZXQgbWVzc2FnZSA9XG4gICAgJ051bGxhYmxlIGV4cHJlc3Npb24gJyArXG4gICAgZXhwciArXG4gICAgXCIgaXMgbm90IGFsbG93ZWQgaW5zaWRlICdcIiArXG4gICAga2xlZW5lRXhwci5vcGVyYXRvciArXG4gICAgXCInIChwb3NzaWJsZSBpbmZpbml0ZSBsb29wKVwiO1xuICBpZiAoYXBwbGljYXRpb25TdGFjay5sZW5ndGggPiAwKSB7XG4gICAgY29uc3Qgc3RhY2tUcmFjZSA9IGFwcGxpY2F0aW9uU3RhY2tcbiAgICAgIC5tYXAoYXBwID0+IG5ldyBwZXhwcnMuQXBwbHkoYXBwLnJ1bGVOYW1lLCBhcHAuYXJncykpXG4gICAgICAuam9pbignXFxuJyk7XG4gICAgbWVzc2FnZSArPSAnXFxuQXBwbGljYXRpb24gc3RhY2sgKG1vc3QgcmVjZW50IGFwcGxpY2F0aW9uIGxhc3QpOlxcbicgKyBzdGFja1RyYWNlO1xuICB9XG4gIHJldHVybiBjcmVhdGVFcnJvcihtZXNzYWdlLCBrbGVlbmVFeHByLmV4cHIuc291cmNlKTtcbn1cblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0gYXJpdHkgLS0tLS0tLS0tLS0tLS0tLS1cblxuZXhwb3J0IGZ1bmN0aW9uIGluY29uc2lzdGVudEFyaXR5KHJ1bGVOYW1lLCBleHBlY3RlZCwgYWN0dWFsLCBleHByKSB7XG4gIHJldHVybiBjcmVhdGVFcnJvcihcbiAgICAnUnVsZSAnICtcbiAgICAgIHJ1bGVOYW1lICtcbiAgICAgICcgaW52b2x2ZXMgYW4gYWx0ZXJuYXRpb24gd2hpY2ggaGFzIGluY29uc2lzdGVudCBhcml0eSAnICtcbiAgICAgICcoZXhwZWN0ZWQgJyArXG4gICAgICBleHBlY3RlZCArXG4gICAgICAnLCBnb3QgJyArXG4gICAgICBhY3R1YWwgK1xuICAgICAgJyknLFxuICAgIGV4cHIuc291cmNlXG4gICk7XG59XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tIHByb3BlcnRpZXMgLS0tLS0tLS0tLS0tLS0tLS1cblxuZXhwb3J0IGZ1bmN0aW9uIGR1cGxpY2F0ZVByb3BlcnR5TmFtZXMoZHVwbGljYXRlcykge1xuICByZXR1cm4gY3JlYXRlRXJyb3IoJ09iamVjdCBwYXR0ZXJuIGhhcyBkdXBsaWNhdGUgcHJvcGVydHkgbmFtZXM6ICcgKyBkdXBsaWNhdGVzLmpvaW4oJywgJykpO1xufVxuXG4vLyAtLS0tLS0tLS0tLS0tLS0tLSBjb25zdHJ1Y3RvcnMgLS0tLS0tLS0tLS0tLS0tLS1cblxuZXhwb3J0IGZ1bmN0aW9uIGludmFsaWRDb25zdHJ1Y3RvckNhbGwoZ3JhbW1hciwgY3Rvck5hbWUsIGNoaWxkcmVuKSB7XG4gIHJldHVybiBjcmVhdGVFcnJvcihcbiAgICAnQXR0ZW1wdCB0byBpbnZva2UgY29uc3RydWN0b3IgJyArIGN0b3JOYW1lICsgJyB3aXRoIGludmFsaWQgb3IgdW5leHBlY3RlZCBhcmd1bWVudHMnXG4gICk7XG59XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tIGNvbnZlbmllbmNlIC0tLS0tLS0tLS0tLS0tLS0tXG5cbmV4cG9ydCBmdW5jdGlvbiBtdWx0aXBsZUVycm9ycyhlcnJvcnMpIHtcbiAgY29uc3QgbWVzc2FnZXMgPSBlcnJvcnMubWFwKGUgPT4gZS5tZXNzYWdlKTtcbiAgcmV0dXJuIGNyZWF0ZUVycm9yKFsnRXJyb3JzOiddLmNvbmNhdChtZXNzYWdlcykuam9pbignXFxuLSAnKSwgZXJyb3JzWzBdLmludGVydmFsKTtcbn1cblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0gc2VtYW50aWMgLS0tLS0tLS0tLS0tLS0tLS1cblxuZXhwb3J0IGZ1bmN0aW9uIG1pc3NpbmdTZW1hbnRpY0FjdGlvbihjdG9yTmFtZSwgbmFtZSwgdHlwZSwgc3RhY2spIHtcbiAgbGV0IHN0YWNrVHJhY2UgPSBzdGFja1xuICAgIC5zbGljZSgwLCAtMSlcbiAgICAubWFwKGluZm8gPT4ge1xuICAgICAgY29uc3QgYW5zID0gJyAgJyArIGluZm9bMF0ubmFtZSArICcgPiAnICsgaW5mb1sxXTtcbiAgICAgIHJldHVybiBpbmZvLmxlbmd0aCA9PT0gMyA/IGFucyArIFwiIGZvciAnXCIgKyBpbmZvWzJdICsgXCInXCIgOiBhbnM7XG4gICAgfSlcbiAgICAuam9pbignXFxuJyk7XG4gIHN0YWNrVHJhY2UgKz0gJ1xcbiAgJyArIG5hbWUgKyAnID4gJyArIGN0b3JOYW1lO1xuXG4gIGxldCBtb3JlSW5mbyA9ICcnO1xuICBpZiAoY3Rvck5hbWUgPT09ICdfaXRlcicpIHtcbiAgICBtb3JlSW5mbyA9IFtcbiAgICAgICdcXG5OT1RFOiBhcyBvZiBPaG0gdjE2LCB0aGVyZSBpcyBubyBkZWZhdWx0IGFjdGlvbiBmb3IgaXRlcmF0aW9uIG5vZGVzIOKAlCBzZWUgJyxcbiAgICAgICcgIGh0dHBzOi8vb2htanMub3JnL2QvZHNhIGZvciBkZXRhaWxzLicsXG4gICAgXS5qb2luKCdcXG4nKTtcbiAgfVxuXG4gIGNvbnN0IG1lc3NhZ2UgPSBbXG4gICAgYE1pc3Npbmcgc2VtYW50aWMgYWN0aW9uIGZvciAnJHtjdG9yTmFtZX0nIGluICR7dHlwZX0gJyR7bmFtZX0nLiR7bW9yZUluZm99YCxcbiAgICAnQWN0aW9uIHN0YWNrIChtb3N0IHJlY2VudCBjYWxsIGxhc3QpOicsXG4gICAgc3RhY2tUcmFjZSxcbiAgXS5qb2luKCdcXG4nKTtcblxuICBjb25zdCBlID0gY3JlYXRlRXJyb3IobWVzc2FnZSk7XG4gIGUubmFtZSA9ICdtaXNzaW5nU2VtYW50aWNBY3Rpb24nO1xuICByZXR1cm4gZTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIHRocm93RXJyb3JzKGVycm9ycykge1xuICBpZiAoZXJyb3JzLmxlbmd0aCA9PT0gMSkge1xuICAgIHRocm93IGVycm9yc1swXTtcbiAgfVxuICBpZiAoZXJyb3JzLmxlbmd0aCA+IDEpIHtcbiAgICB0aHJvdyBtdWx0aXBsZUVycm9ycyhlcnJvcnMpO1xuICB9XG59XG4iLCJpbXBvcnQgKiBhcyBjb21tb24gZnJvbSAnLi9jb21tb24uanMnO1xuXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gUHJpdmF0ZSBzdHVmZlxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cblxuLy8gR2l2ZW4gYW4gYXJyYXkgb2YgbnVtYmVycyBgYXJyYCwgcmV0dXJuIGFuIGFycmF5IG9mIHRoZSBudW1iZXJzIGFzIHN0cmluZ3MsXG4vLyByaWdodC1qdXN0aWZpZWQgYW5kIHBhZGRlZCB0byB0aGUgc2FtZSBsZW5ndGguXG5mdW5jdGlvbiBwYWROdW1iZXJzVG9FcXVhbExlbmd0aChhcnIpIHtcbiAgbGV0IG1heExlbiA9IDA7XG4gIGNvbnN0IHN0cmluZ3MgPSBhcnIubWFwKG4gPT4ge1xuICAgIGNvbnN0IHN0ciA9IG4udG9TdHJpbmcoKTtcbiAgICBtYXhMZW4gPSBNYXRoLm1heChtYXhMZW4sIHN0ci5sZW5ndGgpO1xuICAgIHJldHVybiBzdHI7XG4gIH0pO1xuICByZXR1cm4gc3RyaW5ncy5tYXAocyA9PiBjb21tb24ucGFkTGVmdChzLCBtYXhMZW4pKTtcbn1cblxuLy8gUHJvZHVjZSBhIG5ldyBzdHJpbmcgdGhhdCB3b3VsZCBiZSB0aGUgcmVzdWx0IG9mIGNvcHlpbmcgdGhlIGNvbnRlbnRzXG4vLyBvZiB0aGUgc3RyaW5nIGBzcmNgIG9udG8gYGRlc3RgIGF0IG9mZnNldCBgb2ZmZXN0YC5cbmZ1bmN0aW9uIHN0cmNweShkZXN0LCBzcmMsIG9mZnNldCkge1xuICBjb25zdCBvcmlnRGVzdExlbiA9IGRlc3QubGVuZ3RoO1xuICBjb25zdCBzdGFydCA9IGRlc3Quc2xpY2UoMCwgb2Zmc2V0KTtcbiAgY29uc3QgZW5kID0gZGVzdC5zbGljZShvZmZzZXQgKyBzcmMubGVuZ3RoKTtcbiAgcmV0dXJuIChzdGFydCArIHNyYyArIGVuZCkuc3Vic3RyKDAsIG9yaWdEZXN0TGVuKTtcbn1cblxuLy8gQ2FzdHMgdGhlIHVuZGVybHlpbmcgbGluZUFuZENvbCBvYmplY3QgdG8gYSBmb3JtYXR0ZWQgbWVzc2FnZSBzdHJpbmcsXG4vLyBoaWdobGlnaHRpbmcgYHJhbmdlc2AuXG5mdW5jdGlvbiBsaW5lQW5kQ29sdW1uVG9NZXNzYWdlKC4uLnJhbmdlcykge1xuICBjb25zdCBsaW5lQW5kQ29sID0gdGhpcztcbiAgY29uc3Qge29mZnNldH0gPSBsaW5lQW5kQ29sO1xuICBjb25zdCB7cmVwZWF0U3RyfSA9IGNvbW1vbjtcblxuICBjb25zdCBzYiA9IG5ldyBjb21tb24uU3RyaW5nQnVmZmVyKCk7XG4gIHNiLmFwcGVuZCgnTGluZSAnICsgbGluZUFuZENvbC5saW5lTnVtICsgJywgY29sICcgKyBsaW5lQW5kQ29sLmNvbE51bSArICc6XFxuJyk7XG5cbiAgLy8gQW4gYXJyYXkgb2YgdGhlIHByZXZpb3VzLCBjdXJyZW50LCBhbmQgbmV4dCBsaW5lIG51bWJlcnMgYXMgc3RyaW5ncyBvZiBlcXVhbCBsZW5ndGguXG4gIGNvbnN0IGxpbmVOdW1iZXJzID0gcGFkTnVtYmVyc1RvRXF1YWxMZW5ndGgoW1xuICAgIGxpbmVBbmRDb2wucHJldkxpbmUgPT0gbnVsbCA/IDAgOiBsaW5lQW5kQ29sLmxpbmVOdW0gLSAxLFxuICAgIGxpbmVBbmRDb2wubGluZU51bSxcbiAgICBsaW5lQW5kQ29sLm5leHRMaW5lID09IG51bGwgPyAwIDogbGluZUFuZENvbC5saW5lTnVtICsgMSxcbiAgXSk7XG5cbiAgLy8gSGVscGVyIGZvciBhcHBlbmRpbmcgZm9ybWF0dGluZyBpbnB1dCBsaW5lcyB0byB0aGUgYnVmZmVyLlxuICBjb25zdCBhcHBlbmRMaW5lID0gKG51bSwgY29udGVudCwgcHJlZml4KSA9PiB7XG4gICAgc2IuYXBwZW5kKHByZWZpeCArIGxpbmVOdW1iZXJzW251bV0gKyAnIHwgJyArIGNvbnRlbnQgKyAnXFxuJyk7XG4gIH07XG5cbiAgLy8gSW5jbHVkZSB0aGUgcHJldmlvdXMgbGluZSBmb3IgY29udGV4dCBpZiBwb3NzaWJsZS5cbiAgaWYgKGxpbmVBbmRDb2wucHJldkxpbmUgIT0gbnVsbCkge1xuICAgIGFwcGVuZExpbmUoMCwgbGluZUFuZENvbC5wcmV2TGluZSwgJyAgJyk7XG4gIH1cbiAgLy8gTGluZSB0aGF0IHRoZSBlcnJvciBvY2N1cnJlZCBvbi5cbiAgYXBwZW5kTGluZSgxLCBsaW5lQW5kQ29sLmxpbmUsICc+ICcpO1xuXG4gIC8vIEJ1aWxkIHVwIHRoZSBsaW5lIHRoYXQgcG9pbnRzIHRvIHRoZSBvZmZzZXQgYW5kIHBvc3NpYmxlIGluZGljYXRlcyBvbmUgb3IgbW9yZSByYW5nZXMuXG4gIC8vIFN0YXJ0IHdpdGggYSBibGFuayBsaW5lLCBhbmQgaW5kaWNhdGUgZWFjaCByYW5nZSBieSBvdmVybGF5aW5nIGEgc3RyaW5nIG9mIGB+YCBjaGFycy5cbiAgY29uc3QgbGluZUxlbiA9IGxpbmVBbmRDb2wubGluZS5sZW5ndGg7XG4gIGxldCBpbmRpY2F0aW9uTGluZSA9IHJlcGVhdFN0cignICcsIGxpbmVMZW4gKyAxKTtcbiAgZm9yIChsZXQgaSA9IDA7IGkgPCByYW5nZXMubGVuZ3RoOyArK2kpIHtcbiAgICBsZXQgc3RhcnRJZHggPSByYW5nZXNbaV1bMF07XG4gICAgbGV0IGVuZElkeCA9IHJhbmdlc1tpXVsxXTtcbiAgICBjb21tb24uYXNzZXJ0KHN0YXJ0SWR4ID49IDAgJiYgc3RhcnRJZHggPD0gZW5kSWR4LCAncmFuZ2Ugc3RhcnQgbXVzdCBiZSA+PSAwIGFuZCA8PSBlbmQnKTtcblxuICAgIGNvbnN0IGxpbmVTdGFydE9mZnNldCA9IG9mZnNldCAtIGxpbmVBbmRDb2wuY29sTnVtICsgMTtcbiAgICBzdGFydElkeCA9IE1hdGgubWF4KDAsIHN0YXJ0SWR4IC0gbGluZVN0YXJ0T2Zmc2V0KTtcbiAgICBlbmRJZHggPSBNYXRoLm1pbihlbmRJZHggLSBsaW5lU3RhcnRPZmZzZXQsIGxpbmVMZW4pO1xuXG4gICAgaW5kaWNhdGlvbkxpbmUgPSBzdHJjcHkoaW5kaWNhdGlvbkxpbmUsIHJlcGVhdFN0cignficsIGVuZElkeCAtIHN0YXJ0SWR4KSwgc3RhcnRJZHgpO1xuICB9XG4gIGNvbnN0IGd1dHRlcldpZHRoID0gMiArIGxpbmVOdW1iZXJzWzFdLmxlbmd0aCArIDM7XG4gIHNiLmFwcGVuZChyZXBlYXRTdHIoJyAnLCBndXR0ZXJXaWR0aCkpO1xuICBpbmRpY2F0aW9uTGluZSA9IHN0cmNweShpbmRpY2F0aW9uTGluZSwgJ14nLCBsaW5lQW5kQ29sLmNvbE51bSAtIDEpO1xuICBzYi5hcHBlbmQoaW5kaWNhdGlvbkxpbmUucmVwbGFjZSgvICskLywgJycpICsgJ1xcbicpO1xuXG4gIC8vIEluY2x1ZGUgdGhlIG5leHQgbGluZSBmb3IgY29udGV4dCBpZiBwb3NzaWJsZS5cbiAgaWYgKGxpbmVBbmRDb2wubmV4dExpbmUgIT0gbnVsbCkge1xuICAgIGFwcGVuZExpbmUoMiwgbGluZUFuZENvbC5uZXh0TGluZSwgJyAgJyk7XG4gIH1cbiAgcmV0dXJuIHNiLmNvbnRlbnRzKCk7XG59XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG4vLyBFeHBvcnRzXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuXG5sZXQgYnVpbHRJblJ1bGVzQ2FsbGJhY2tzID0gW107XG5cbi8vIFNpbmNlIEdyYW1tYXIuQnVpbHRJblJ1bGVzIGlzIGJvb3RzdHJhcHBlZCwgbW9zdCBvZiBPaG0gY2FuJ3QgZGlyZWN0bHkgZGVwZW5kIGl0LlxuLy8gVGhpcyBmdW5jdGlvbiBhbGxvd3MgbW9kdWxlcyB0aGF0IGRvIGRlcGVuZCBvbiB0aGUgYnVpbHQtaW4gcnVsZXMgdG8gcmVnaXN0ZXIgYSBjYWxsYmFja1xuLy8gdGhhdCB3aWxsIGJlIGNhbGxlZCBsYXRlciBpbiB0aGUgaW5pdGlhbGl6YXRpb24gcHJvY2Vzcy5cbmV4cG9ydCBmdW5jdGlvbiBhd2FpdEJ1aWx0SW5SdWxlcyhjYikge1xuICBidWlsdEluUnVsZXNDYWxsYmFja3MucHVzaChjYik7XG59XG5cbmV4cG9ydCBmdW5jdGlvbiBhbm5vdW5jZUJ1aWx0SW5SdWxlcyhncmFtbWFyKSB7XG4gIGJ1aWx0SW5SdWxlc0NhbGxiYWNrcy5mb3JFYWNoKGNiID0+IHtcbiAgICBjYihncmFtbWFyKTtcbiAgfSk7XG4gIGJ1aWx0SW5SdWxlc0NhbGxiYWNrcyA9IG51bGw7XG59XG5cbi8vIFJldHVybiBhbiBvYmplY3Qgd2l0aCB0aGUgbGluZSBhbmQgY29sdW1uIGluZm9ybWF0aW9uIGZvciB0aGUgZ2l2ZW5cbi8vIG9mZnNldCBpbiBgc3RyYC5cbmV4cG9ydCBmdW5jdGlvbiBnZXRMaW5lQW5kQ29sdW1uKHN0ciwgb2Zmc2V0KSB7XG4gIGxldCBsaW5lTnVtID0gMTtcbiAgbGV0IGNvbE51bSA9IDE7XG5cbiAgbGV0IGN1cnJPZmZzZXQgPSAwO1xuICBsZXQgbGluZVN0YXJ0T2Zmc2V0ID0gMDtcblxuICBsZXQgbmV4dExpbmUgPSBudWxsO1xuICBsZXQgcHJldkxpbmUgPSBudWxsO1xuICBsZXQgcHJldkxpbmVTdGFydE9mZnNldCA9IC0xO1xuXG4gIHdoaWxlIChjdXJyT2Zmc2V0IDwgb2Zmc2V0KSB7XG4gICAgY29uc3QgYyA9IHN0ci5jaGFyQXQoY3Vyck9mZnNldCsrKTtcbiAgICBpZiAoYyA9PT0gJ1xcbicpIHtcbiAgICAgIGxpbmVOdW0rKztcbiAgICAgIGNvbE51bSA9IDE7XG4gICAgICBwcmV2TGluZVN0YXJ0T2Zmc2V0ID0gbGluZVN0YXJ0T2Zmc2V0O1xuICAgICAgbGluZVN0YXJ0T2Zmc2V0ID0gY3Vyck9mZnNldDtcbiAgICB9IGVsc2UgaWYgKGMgIT09ICdcXHInKSB7XG4gICAgICBjb2xOdW0rKztcbiAgICB9XG4gIH1cblxuICAvLyBGaW5kIHRoZSBlbmQgb2YgdGhlIHRhcmdldCBsaW5lLlxuICBsZXQgbGluZUVuZE9mZnNldCA9IHN0ci5pbmRleE9mKCdcXG4nLCBsaW5lU3RhcnRPZmZzZXQpO1xuICBpZiAobGluZUVuZE9mZnNldCA9PT0gLTEpIHtcbiAgICBsaW5lRW5kT2Zmc2V0ID0gc3RyLmxlbmd0aDtcbiAgfSBlbHNlIHtcbiAgICAvLyBHZXQgdGhlIG5leHQgbGluZS5cbiAgICBjb25zdCBuZXh0TGluZUVuZE9mZnNldCA9IHN0ci5pbmRleE9mKCdcXG4nLCBsaW5lRW5kT2Zmc2V0ICsgMSk7XG4gICAgbmV4dExpbmUgPVxuICAgICAgbmV4dExpbmVFbmRPZmZzZXQgPT09IC0xXG4gICAgICAgID8gc3RyLnNsaWNlKGxpbmVFbmRPZmZzZXQpXG4gICAgICAgIDogc3RyLnNsaWNlKGxpbmVFbmRPZmZzZXQsIG5leHRMaW5lRW5kT2Zmc2V0KTtcbiAgICAvLyBTdHJpcCBsZWFkaW5nIGFuZCB0cmFpbGluZyBFT0wgY2hhcihzKS5cbiAgICBuZXh0TGluZSA9IG5leHRMaW5lLnJlcGxhY2UoL15cXHI/XFxuLywgJycpLnJlcGxhY2UoL1xcciQvLCAnJyk7XG4gIH1cblxuICAvLyBHZXQgdGhlIHByZXZpb3VzIGxpbmUuXG4gIGlmIChwcmV2TGluZVN0YXJ0T2Zmc2V0ID49IDApIHtcbiAgICAvLyBTdHJpcCB0cmFpbGluZyBFT0wgY2hhcihzKS5cbiAgICBwcmV2TGluZSA9IHN0ci5zbGljZShwcmV2TGluZVN0YXJ0T2Zmc2V0LCBsaW5lU3RhcnRPZmZzZXQpLnJlcGxhY2UoL1xccj9cXG4kLywgJycpO1xuICB9XG5cbiAgLy8gR2V0IHRoZSB0YXJnZXQgbGluZSwgc3RyaXBwaW5nIGEgdHJhaWxpbmcgY2FycmlhZ2UgcmV0dXJuIGlmIG5lY2Vzc2FyeS5cbiAgY29uc3QgbGluZSA9IHN0ci5zbGljZShsaW5lU3RhcnRPZmZzZXQsIGxpbmVFbmRPZmZzZXQpLnJlcGxhY2UoL1xcciQvLCAnJyk7XG5cbiAgcmV0dXJuIHtcbiAgICBvZmZzZXQsXG4gICAgbGluZU51bSxcbiAgICBjb2xOdW0sXG4gICAgbGluZSxcbiAgICBwcmV2TGluZSxcbiAgICBuZXh0TGluZSxcbiAgICB0b1N0cmluZzogbGluZUFuZENvbHVtblRvTWVzc2FnZSxcbiAgfTtcbn1cblxuLy8gUmV0dXJuIGEgbmljZWx5LWZvcm1hdHRlZCBzdHJpbmcgZGVzY3JpYmluZyB0aGUgbGluZSBhbmQgY29sdW1uIGZvciB0aGVcbi8vIGdpdmVuIG9mZnNldCBpbiBgc3RyYCBoaWdobGlnaHRpbmcgYHJhbmdlc2AuXG5leHBvcnQgZnVuY3Rpb24gZ2V0TGluZUFuZENvbHVtbk1lc3NhZ2Uoc3RyLCBvZmZzZXQsIC4uLnJhbmdlcykge1xuICByZXR1cm4gZ2V0TGluZUFuZENvbHVtbihzdHIsIG9mZnNldCkudG9TdHJpbmcoLi4ucmFuZ2VzKTtcbn1cblxuZXhwb3J0IGNvbnN0IHVuaXF1ZUlkID0gKCgpID0+IHtcbiAgbGV0IGlkQ291bnRlciA9IDA7XG4gIHJldHVybiBwcmVmaXggPT4gJycgKyBwcmVmaXggKyBpZENvdW50ZXIrKztcbn0pKCk7XG4iLCJpbXBvcnQge2Fzc2VydH0gZnJvbSAnLi9jb21tb24uanMnO1xuaW1wb3J0ICogYXMgZXJyb3JzIGZyb20gJy4vZXJyb3JzLmpzJztcbmltcG9ydCAqIGFzIHV0aWwgZnJvbSAnLi91dGlsLmpzJztcblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cbi8vIFByaXZhdGUgc3R1ZmZcbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG5cbmV4cG9ydCBjbGFzcyBJbnRlcnZhbCB7XG4gIGNvbnN0cnVjdG9yKHNvdXJjZVN0cmluZywgc3RhcnRJZHgsIGVuZElkeCkge1xuICAgIC8vIFN0b3JlIHRoZSBmdWxsIHNvdXJjZSBpbiBhIG5vbi1lbnVtZXJhYmxlIHByb3BlcnR5LCBzbyB0aGF0IHdoZW5cbiAgICAvLyBncmFtbWFycyBhbmQgb3RoZXIgb2JqZWN0cyBhcmUgcHJpbnRlZCBpbiB0aGUgUkVQTCwgaXQncyBub3RcbiAgICAvLyBjbHV0dGVyZWQgd2l0aCBtdWx0aXBsZSBjb3BpZXMgb2YgdGhlIHNhbWUgbG9uZyBzdHJpbmcuXG4gICAgT2JqZWN0LmRlZmluZVByb3BlcnR5KHRoaXMsICdfc291cmNlU3RyaW5nJywge1xuICAgICAgdmFsdWU6IHNvdXJjZVN0cmluZyxcbiAgICAgIGNvbmZpZ3VyYWJsZTogZmFsc2UsXG4gICAgICBlbnVtZXJhYmxlOiBmYWxzZSxcbiAgICAgIHdyaXRhYmxlOiBmYWxzZSxcbiAgICB9KTtcbiAgICB0aGlzLnN0YXJ0SWR4ID0gc3RhcnRJZHg7XG4gICAgdGhpcy5lbmRJZHggPSBlbmRJZHg7XG4gIH1cblxuICBnZXQgc291cmNlU3RyaW5nKCkge1xuICAgIHJldHVybiB0aGlzLl9zb3VyY2VTdHJpbmc7XG4gIH1cblxuICBnZXQgY29udGVudHMoKSB7XG4gICAgaWYgKHRoaXMuX2NvbnRlbnRzID09PSB1bmRlZmluZWQpIHtcbiAgICAgIHRoaXMuX2NvbnRlbnRzID0gdGhpcy5zb3VyY2VTdHJpbmcuc2xpY2UodGhpcy5zdGFydElkeCwgdGhpcy5lbmRJZHgpO1xuICAgIH1cbiAgICByZXR1cm4gdGhpcy5fY29udGVudHM7XG4gIH1cblxuICBnZXQgbGVuZ3RoKCkge1xuICAgIHJldHVybiB0aGlzLmVuZElkeCAtIHRoaXMuc3RhcnRJZHg7XG4gIH1cblxuICBjb3ZlcmFnZVdpdGgoLi4uaW50ZXJ2YWxzKSB7XG4gICAgcmV0dXJuIEludGVydmFsLmNvdmVyYWdlKC4uLmludGVydmFscywgdGhpcyk7XG4gIH1cblxuICBjb2xsYXBzZWRMZWZ0KCkge1xuICAgIHJldHVybiBuZXcgSW50ZXJ2YWwodGhpcy5zb3VyY2VTdHJpbmcsIHRoaXMuc3RhcnRJZHgsIHRoaXMuc3RhcnRJZHgpO1xuICB9XG5cbiAgY29sbGFwc2VkUmlnaHQoKSB7XG4gICAgcmV0dXJuIG5ldyBJbnRlcnZhbCh0aGlzLnNvdXJjZVN0cmluZywgdGhpcy5lbmRJZHgsIHRoaXMuZW5kSWR4KTtcbiAgfVxuXG4gIGdldExpbmVBbmRDb2x1bW4oKSB7XG4gICAgcmV0dXJuIHV0aWwuZ2V0TGluZUFuZENvbHVtbih0aGlzLnNvdXJjZVN0cmluZywgdGhpcy5zdGFydElkeCk7XG4gIH1cblxuICBnZXRMaW5lQW5kQ29sdW1uTWVzc2FnZSgpIHtcbiAgICBjb25zdCByYW5nZSA9IFt0aGlzLnN0YXJ0SWR4LCB0aGlzLmVuZElkeF07XG4gICAgcmV0dXJuIHV0aWwuZ2V0TGluZUFuZENvbHVtbk1lc3NhZ2UodGhpcy5zb3VyY2VTdHJpbmcsIHRoaXMuc3RhcnRJZHgsIHJhbmdlKTtcbiAgfVxuXG4gIC8vIFJldHVybnMgYW4gYXJyYXkgb2YgMCwgMSwgb3IgMiBpbnRlcnZhbHMgdGhhdCByZXByZXNlbnRzIHRoZSByZXN1bHQgb2YgdGhlXG4gIC8vIGludGVydmFsIGRpZmZlcmVuY2Ugb3BlcmF0aW9uLlxuICBtaW51cyh0aGF0KSB7XG4gICAgaWYgKHRoaXMuc291cmNlU3RyaW5nICE9PSB0aGF0LnNvdXJjZVN0cmluZykge1xuICAgICAgdGhyb3cgZXJyb3JzLmludGVydmFsU291cmNlc0RvbnRNYXRjaCgpO1xuICAgIH0gZWxzZSBpZiAodGhpcy5zdGFydElkeCA9PT0gdGhhdC5zdGFydElkeCAmJiB0aGlzLmVuZElkeCA9PT0gdGhhdC5lbmRJZHgpIHtcbiAgICAgIC8vIGB0aGlzYCBhbmQgYHRoYXRgIGFyZSB0aGUgc2FtZSBpbnRlcnZhbCFcbiAgICAgIHJldHVybiBbXTtcbiAgICB9IGVsc2UgaWYgKHRoaXMuc3RhcnRJZHggPCB0aGF0LnN0YXJ0SWR4ICYmIHRoYXQuZW5kSWR4IDwgdGhpcy5lbmRJZHgpIHtcbiAgICAgIC8vIGB0aGF0YCBzcGxpdHMgYHRoaXNgIGludG8gdHdvIGludGVydmFsc1xuICAgICAgcmV0dXJuIFtcbiAgICAgICAgbmV3IEludGVydmFsKHRoaXMuc291cmNlU3RyaW5nLCB0aGlzLnN0YXJ0SWR4LCB0aGF0LnN0YXJ0SWR4KSxcbiAgICAgICAgbmV3IEludGVydmFsKHRoaXMuc291cmNlU3RyaW5nLCB0aGF0LmVuZElkeCwgdGhpcy5lbmRJZHgpLFxuICAgICAgXTtcbiAgICB9IGVsc2UgaWYgKHRoaXMuc3RhcnRJZHggPCB0aGF0LmVuZElkeCAmJiB0aGF0LmVuZElkeCA8IHRoaXMuZW5kSWR4KSB7XG4gICAgICAvLyBgdGhhdGAgY29udGFpbnMgYSBwcmVmaXggb2YgYHRoaXNgXG4gICAgICByZXR1cm4gW25ldyBJbnRlcnZhbCh0aGlzLnNvdXJjZVN0cmluZywgdGhhdC5lbmRJZHgsIHRoaXMuZW5kSWR4KV07XG4gICAgfSBlbHNlIGlmICh0aGlzLnN0YXJ0SWR4IDwgdGhhdC5zdGFydElkeCAmJiB0aGF0LnN0YXJ0SWR4IDwgdGhpcy5lbmRJZHgpIHtcbiAgICAgIC8vIGB0aGF0YCBjb250YWlucyBhIHN1ZmZpeCBvZiBgdGhpc2BcbiAgICAgIHJldHVybiBbbmV3IEludGVydmFsKHRoaXMuc291cmNlU3RyaW5nLCB0aGlzLnN0YXJ0SWR4LCB0aGF0LnN0YXJ0SWR4KV07XG4gICAgfSBlbHNlIHtcbiAgICAgIC8vIGB0aGF0YCBhbmQgYHRoaXNgIGRvIG5vdCBvdmVybGFwXG4gICAgICByZXR1cm4gW3RoaXNdO1xuICAgIH1cbiAgfVxuXG4gIC8vIFJldHVybnMgYSBuZXcgSW50ZXJ2YWwgdGhhdCBoYXMgdGhlIHNhbWUgZXh0ZW50IGFzIHRoaXMgb25lLCBidXQgd2hpY2ggaXMgcmVsYXRpdmVcbiAgLy8gdG8gYHRoYXRgLCBhbiBJbnRlcnZhbCB0aGF0IGZ1bGx5IGNvdmVycyB0aGlzIG9uZS5cbiAgcmVsYXRpdmVUbyh0aGF0KSB7XG4gICAgaWYgKHRoaXMuc291cmNlU3RyaW5nICE9PSB0aGF0LnNvdXJjZVN0cmluZykge1xuICAgICAgdGhyb3cgZXJyb3JzLmludGVydmFsU291cmNlc0RvbnRNYXRjaCgpO1xuICAgIH1cbiAgICBhc3NlcnQoXG4gICAgICB0aGlzLnN0YXJ0SWR4ID49IHRoYXQuc3RhcnRJZHggJiYgdGhpcy5lbmRJZHggPD0gdGhhdC5lbmRJZHgsXG4gICAgICAnb3RoZXIgaW50ZXJ2YWwgZG9lcyBub3QgY292ZXIgdGhpcyBvbmUnXG4gICAgKTtcbiAgICByZXR1cm4gbmV3IEludGVydmFsKFxuICAgICAgdGhpcy5zb3VyY2VTdHJpbmcsXG4gICAgICB0aGlzLnN0YXJ0SWR4IC0gdGhhdC5zdGFydElkeCxcbiAgICAgIHRoaXMuZW5kSWR4IC0gdGhhdC5zdGFydElkeFxuICAgICk7XG4gIH1cblxuICAvLyBSZXR1cm5zIGEgbmV3IEludGVydmFsIHdoaWNoIGNvbnRhaW5zIHRoZSBzYW1lIGNvbnRlbnRzIGFzIHRoaXMgb25lLFxuICAvLyBidXQgd2l0aCB3aGl0ZXNwYWNlIHRyaW1tZWQgZnJvbSBib3RoIGVuZHMuXG4gIHRyaW1tZWQoKSB7XG4gICAgY29uc3Qge2NvbnRlbnRzfSA9IHRoaXM7XG4gICAgY29uc3Qgc3RhcnRJZHggPSB0aGlzLnN0YXJ0SWR4ICsgY29udGVudHMubWF0Y2goL15cXHMqLylbMF0ubGVuZ3RoO1xuICAgIGNvbnN0IGVuZElkeCA9IHRoaXMuZW5kSWR4IC0gY29udGVudHMubWF0Y2goL1xccyokLylbMF0ubGVuZ3RoO1xuICAgIHJldHVybiBuZXcgSW50ZXJ2YWwodGhpcy5zb3VyY2VTdHJpbmcsIHN0YXJ0SWR4LCBlbmRJZHgpO1xuICB9XG5cbiAgc3ViSW50ZXJ2YWwob2Zmc2V0LCBsZW4pIHtcbiAgICBjb25zdCBuZXdTdGFydElkeCA9IHRoaXMuc3RhcnRJZHggKyBvZmZzZXQ7XG4gICAgcmV0dXJuIG5ldyBJbnRlcnZhbCh0aGlzLnNvdXJjZVN0cmluZywgbmV3U3RhcnRJZHgsIG5ld1N0YXJ0SWR4ICsgbGVuKTtcbiAgfVxufVxuXG5JbnRlcnZhbC5jb3ZlcmFnZSA9IGZ1bmN0aW9uIChmaXJzdEludGVydmFsLCAuLi5pbnRlcnZhbHMpIHtcbiAgbGV0IHtzdGFydElkeCwgZW5kSWR4fSA9IGZpcnN0SW50ZXJ2YWw7XG4gIGZvciAoY29uc3QgaW50ZXJ2YWwgb2YgaW50ZXJ2YWxzKSB7XG4gICAgaWYgKGludGVydmFsLnNvdXJjZVN0cmluZyAhPT0gZmlyc3RJbnRlcnZhbC5zb3VyY2VTdHJpbmcpIHtcbiAgICAgIHRocm93IGVycm9ycy5pbnRlcnZhbFNvdXJjZXNEb250TWF0Y2goKTtcbiAgICB9IGVsc2Uge1xuICAgICAgc3RhcnRJZHggPSBNYXRoLm1pbihzdGFydElkeCwgaW50ZXJ2YWwuc3RhcnRJZHgpO1xuICAgICAgZW5kSWR4ID0gTWF0aC5tYXgoZW5kSWR4LCBpbnRlcnZhbC5lbmRJZHgpO1xuICAgIH1cbiAgfVxuICByZXR1cm4gbmV3IEludGVydmFsKGZpcnN0SW50ZXJ2YWwuc291cmNlU3RyaW5nLCBzdGFydElkeCwgZW5kSWR4KTtcbn07XG4iLCJpbXBvcnQge0ludGVydmFsfSBmcm9tICcuL0ludGVydmFsLmpzJztcblxuY29uc3QgTUFYX0NIQVJfQ09ERSA9IDB4ZmZmZjtcbmV4cG9ydCBjb25zdCBNQVhfQ09ERV9QT0lOVCA9IDB4MTBmZmZmO1xuXG5leHBvcnQgY2xhc3MgSW5wdXRTdHJlYW0ge1xuICBjb25zdHJ1Y3Rvcihzb3VyY2UpIHtcbiAgICB0aGlzLnNvdXJjZSA9IHNvdXJjZTtcbiAgICB0aGlzLnBvcyA9IDA7XG4gICAgdGhpcy5leGFtaW5lZExlbmd0aCA9IDA7XG4gIH1cblxuICBhdEVuZCgpIHtcbiAgICBjb25zdCBhbnMgPSB0aGlzLnBvcyA+PSB0aGlzLnNvdXJjZS5sZW5ndGg7XG4gICAgdGhpcy5leGFtaW5lZExlbmd0aCA9IE1hdGgubWF4KHRoaXMuZXhhbWluZWRMZW5ndGgsIHRoaXMucG9zICsgMSk7XG4gICAgcmV0dXJuIGFucztcbiAgfVxuXG4gIG5leHQoKSB7XG4gICAgY29uc3QgYW5zID0gdGhpcy5zb3VyY2VbdGhpcy5wb3MrK107XG4gICAgdGhpcy5leGFtaW5lZExlbmd0aCA9IE1hdGgubWF4KHRoaXMuZXhhbWluZWRMZW5ndGgsIHRoaXMucG9zKTtcbiAgICByZXR1cm4gYW5zO1xuICB9XG5cbiAgbmV4dENoYXJDb2RlKCkge1xuICAgIGNvbnN0IG5leHRDaGFyID0gdGhpcy5uZXh0KCk7XG4gICAgcmV0dXJuIG5leHRDaGFyICYmIG5leHRDaGFyLmNoYXJDb2RlQXQoMCk7XG4gIH1cblxuICBuZXh0Q29kZVBvaW50KCkge1xuICAgIGNvbnN0IGNwID0gdGhpcy5zb3VyY2Uuc2xpY2UodGhpcy5wb3MrKykuY29kZVBvaW50QXQoMCk7XG4gICAgLy8gSWYgdGhlIGNvZGUgcG9pbnQgaXMgYmV5b25kIHBsYW5lIDAsIGl0IHRha2VzIHVwIHR3byBjaGFyYWN0ZXJzLlxuICAgIGlmIChjcCA+IE1BWF9DSEFSX0NPREUpIHtcbiAgICAgIHRoaXMucG9zICs9IDE7XG4gICAgfVxuICAgIHRoaXMuZXhhbWluZWRMZW5ndGggPSBNYXRoLm1heCh0aGlzLmV4YW1pbmVkTGVuZ3RoLCB0aGlzLnBvcyk7XG4gICAgcmV0dXJuIGNwO1xuICB9XG5cbiAgbWF0Y2hTdHJpbmcocywgb3B0SWdub3JlQ2FzZSkge1xuICAgIGxldCBpZHg7XG4gICAgaWYgKG9wdElnbm9yZUNhc2UpIHtcbiAgICAgIC8qXG4gICAgICAgIENhc2UtaW5zZW5zaXRpdmUgY29tcGFyaXNvbiBpcyBhIHRyaWNreSBidXNpbmVzcy4gU29tZSBub3RhYmxlIGdvdGNoYXMgaW5jbHVkZSB0aGVcbiAgICAgICAgXCJUdXJraXNoIElcIiBwcm9ibGVtIChodHRwOi8vd3d3LmkxOG5ndXkuY29tL3VuaWNvZGUvdHVya2lzaC1pMThuLmh0bWwpIGFuZCB0aGUgZmFjdFxuICAgICAgICB0aGF0IHRoZSBHZXJtYW4gRXNzemV0ICjDnykgdHVybnMgaW50byBcIlNTXCIgaW4gdXBwZXIgY2FzZS5cblxuICAgICAgICBUaGlzIGlzIGludGVuZGVkIHRvIGJlIGEgbG9jYWxlLWludmFyaWFudCBjb21wYXJpc29uLCB3aGljaCBtZWFucyBpdCBtYXkgbm90IG9iZXlcbiAgICAgICAgbG9jYWxlLXNwZWNpZmljIGV4cGVjdGF0aW9ucyAoZS5nLiBcImlcIiA9PiBcIsSwXCIpLlxuXG4gICAgICAgIFNlZSBhbHNvIGh0dHBzOi8vdW5pY29kZS5vcmcvZmFxL2Nhc2VtYXBfY2hhcnByb3AuaHRtbCNjYXNlbWFwXG4gICAgICAgKi9cbiAgICAgIGZvciAoaWR4ID0gMDsgaWR4IDwgcy5sZW5ndGg7IGlkeCsrKSB7XG4gICAgICAgIGNvbnN0IGFjdHVhbCA9IHRoaXMubmV4dCgpO1xuICAgICAgICBjb25zdCBleHBlY3RlZCA9IHNbaWR4XTtcbiAgICAgICAgaWYgKGFjdHVhbCA9PSBudWxsIHx8IGFjdHVhbC50b1VwcGVyQ2FzZSgpICE9PSBleHBlY3RlZC50b1VwcGVyQ2FzZSgpKSB7XG4gICAgICAgICAgcmV0dXJuIGZhbHNlO1xuICAgICAgICB9XG4gICAgICB9XG4gICAgICByZXR1cm4gdHJ1ZTtcbiAgICB9XG4gICAgLy8gRGVmYXVsdCBpcyBjYXNlLXNlbnNpdGl2ZSBjb21wYXJpc29uLlxuICAgIGZvciAoaWR4ID0gMDsgaWR4IDwgcy5sZW5ndGg7IGlkeCsrKSB7XG4gICAgICBpZiAodGhpcy5uZXh0KCkgIT09IHNbaWR4XSkge1xuICAgICAgICByZXR1cm4gZmFsc2U7XG4gICAgICB9XG4gICAgfVxuICAgIHJldHVybiB0cnVlO1xuICB9XG5cbiAgc291cmNlU2xpY2Uoc3RhcnRJZHgsIGVuZElkeCkge1xuICAgIHJldHVybiB0aGlzLnNvdXJjZS5zbGljZShzdGFydElkeCwgZW5kSWR4KTtcbiAgfVxuXG4gIGludGVydmFsKHN0YXJ0SWR4LCBvcHRFbmRJZHgpIHtcbiAgICByZXR1cm4gbmV3IEludGVydmFsKHRoaXMuc291cmNlLCBzdGFydElkeCwgb3B0RW5kSWR4ID8gb3B0RW5kSWR4IDogdGhpcy5wb3MpO1xuICB9XG59XG4iLCJpbXBvcnQgKiBhcyBjb21tb24gZnJvbSAnLi9jb21tb24uanMnO1xuaW1wb3J0ICogYXMgdXRpbCBmcm9tICcuL3V0aWwuanMnO1xuaW1wb3J0IHtJbnRlcnZhbH0gZnJvbSAnLi9JbnRlcnZhbC5qcyc7XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG4vLyBQcml2YXRlIHN0dWZmXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuXG5leHBvcnQgY2xhc3MgTWF0Y2hSZXN1bHQge1xuICBjb25zdHJ1Y3RvcihcbiAgICBtYXRjaGVyLFxuICAgIGlucHV0LFxuICAgIHN0YXJ0RXhwcixcbiAgICBjc3QsXG4gICAgY3N0T2Zmc2V0LFxuICAgIHJpZ2h0bW9zdEZhaWx1cmVQb3NpdGlvbixcbiAgICBvcHRSZWNvcmRlZEZhaWx1cmVzXG4gICkge1xuICAgIHRoaXMubWF0Y2hlciA9IG1hdGNoZXI7XG4gICAgdGhpcy5pbnB1dCA9IGlucHV0O1xuICAgIHRoaXMuc3RhcnRFeHByID0gc3RhcnRFeHByO1xuICAgIHRoaXMuX2NzdCA9IGNzdDtcbiAgICB0aGlzLl9jc3RPZmZzZXQgPSBjc3RPZmZzZXQ7XG4gICAgdGhpcy5fcmlnaHRtb3N0RmFpbHVyZVBvc2l0aW9uID0gcmlnaHRtb3N0RmFpbHVyZVBvc2l0aW9uO1xuICAgIHRoaXMuX3JpZ2h0bW9zdEZhaWx1cmVzID0gb3B0UmVjb3JkZWRGYWlsdXJlcztcblxuICAgIGlmICh0aGlzLmZhaWxlZCgpKSB7XG4gICAgICBjb21tb24uZGVmaW5lTGF6eVByb3BlcnR5KHRoaXMsICdtZXNzYWdlJywgZnVuY3Rpb24gKCkge1xuICAgICAgICBjb25zdCBkZXRhaWwgPSAnRXhwZWN0ZWQgJyArIHRoaXMuZ2V0RXhwZWN0ZWRUZXh0KCk7XG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgdXRpbC5nZXRMaW5lQW5kQ29sdW1uTWVzc2FnZSh0aGlzLmlucHV0LCB0aGlzLmdldFJpZ2h0bW9zdEZhaWx1cmVQb3NpdGlvbigpKSArIGRldGFpbFxuICAgICAgICApO1xuICAgICAgfSk7XG4gICAgICBjb21tb24uZGVmaW5lTGF6eVByb3BlcnR5KHRoaXMsICdzaG9ydE1lc3NhZ2UnLCBmdW5jdGlvbiAoKSB7XG4gICAgICAgIGNvbnN0IGRldGFpbCA9ICdleHBlY3RlZCAnICsgdGhpcy5nZXRFeHBlY3RlZFRleHQoKTtcbiAgICAgICAgY29uc3QgZXJyb3JJbmZvID0gdXRpbC5nZXRMaW5lQW5kQ29sdW1uKFxuICAgICAgICAgIHRoaXMuaW5wdXQsXG4gICAgICAgICAgdGhpcy5nZXRSaWdodG1vc3RGYWlsdXJlUG9zaXRpb24oKVxuICAgICAgICApO1xuICAgICAgICByZXR1cm4gJ0xpbmUgJyArIGVycm9ySW5mby5saW5lTnVtICsgJywgY29sICcgKyBlcnJvckluZm8uY29sTnVtICsgJzogJyArIGRldGFpbDtcbiAgICAgIH0pO1xuICAgIH1cbiAgfVxuXG4gIHN1Y2NlZWRlZCgpIHtcbiAgICByZXR1cm4gISF0aGlzLl9jc3Q7XG4gIH1cblxuICBmYWlsZWQoKSB7XG4gICAgcmV0dXJuICF0aGlzLnN1Y2NlZWRlZCgpO1xuICB9XG5cbiAgZ2V0UmlnaHRtb3N0RmFpbHVyZVBvc2l0aW9uKCkge1xuICAgIHJldHVybiB0aGlzLl9yaWdodG1vc3RGYWlsdXJlUG9zaXRpb247XG4gIH1cblxuICBnZXRSaWdodG1vc3RGYWlsdXJlcygpIHtcbiAgICBpZiAoIXRoaXMuX3JpZ2h0bW9zdEZhaWx1cmVzKSB7XG4gICAgICB0aGlzLm1hdGNoZXIuc2V0SW5wdXQodGhpcy5pbnB1dCk7XG4gICAgICBjb25zdCBtYXRjaFJlc3VsdFdpdGhGYWlsdXJlcyA9IHRoaXMubWF0Y2hlci5fbWF0Y2godGhpcy5zdGFydEV4cHIsIHtcbiAgICAgICAgdHJhY2luZzogZmFsc2UsXG4gICAgICAgIHBvc2l0aW9uVG9SZWNvcmRGYWlsdXJlczogdGhpcy5nZXRSaWdodG1vc3RGYWlsdXJlUG9zaXRpb24oKSxcbiAgICAgIH0pO1xuICAgICAgdGhpcy5fcmlnaHRtb3N0RmFpbHVyZXMgPSBtYXRjaFJlc3VsdFdpdGhGYWlsdXJlcy5nZXRSaWdodG1vc3RGYWlsdXJlcygpO1xuICAgIH1cbiAgICByZXR1cm4gdGhpcy5fcmlnaHRtb3N0RmFpbHVyZXM7XG4gIH1cblxuICB0b1N0cmluZygpIHtcbiAgICByZXR1cm4gdGhpcy5zdWNjZWVkZWQoKVxuICAgICAgPyAnW21hdGNoIHN1Y2NlZWRlZF0nXG4gICAgICA6ICdbbWF0Y2ggZmFpbGVkIGF0IHBvc2l0aW9uICcgKyB0aGlzLmdldFJpZ2h0bW9zdEZhaWx1cmVQb3NpdGlvbigpICsgJ10nO1xuICB9XG5cbiAgLy8gUmV0dXJuIGEgc3RyaW5nIHN1bW1hcml6aW5nIHRoZSBleHBlY3RlZCBjb250ZW50cyBvZiB0aGUgaW5wdXQgc3RyZWFtIHdoZW5cbiAgLy8gdGhlIG1hdGNoIGZhaWx1cmUgb2NjdXJyZWQuXG4gIGdldEV4cGVjdGVkVGV4dCgpIHtcbiAgICBpZiAodGhpcy5zdWNjZWVkZWQoKSkge1xuICAgICAgdGhyb3cgbmV3IEVycm9yKCdjYW5ub3QgZ2V0IGV4cGVjdGVkIHRleHQgb2YgYSBzdWNjZXNzZnVsIE1hdGNoUmVzdWx0Jyk7XG4gICAgfVxuXG4gICAgY29uc3Qgc2IgPSBuZXcgY29tbW9uLlN0cmluZ0J1ZmZlcigpO1xuICAgIGxldCBmYWlsdXJlcyA9IHRoaXMuZ2V0UmlnaHRtb3N0RmFpbHVyZXMoKTtcblxuICAgIC8vIEZpbHRlciBvdXQgdGhlIGZsdWZmeSBmYWlsdXJlcyB0byBtYWtlIHRoZSBkZWZhdWx0IGVycm9yIG1lc3NhZ2VzIG1vcmUgdXNlZnVsXG4gICAgZmFpbHVyZXMgPSBmYWlsdXJlcy5maWx0ZXIoZmFpbHVyZSA9PiAhZmFpbHVyZS5pc0ZsdWZmeSgpKTtcblxuICAgIGZvciAobGV0IGlkeCA9IDA7IGlkeCA8IGZhaWx1cmVzLmxlbmd0aDsgaWR4KyspIHtcbiAgICAgIGlmIChpZHggPiAwKSB7XG4gICAgICAgIGlmIChpZHggPT09IGZhaWx1cmVzLmxlbmd0aCAtIDEpIHtcbiAgICAgICAgICBzYi5hcHBlbmQoZmFpbHVyZXMubGVuZ3RoID4gMiA/ICcsIG9yICcgOiAnIG9yICcpO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHNiLmFwcGVuZCgnLCAnKTtcbiAgICAgICAgfVxuICAgICAgfVxuICAgICAgc2IuYXBwZW5kKGZhaWx1cmVzW2lkeF0udG9TdHJpbmcoKSk7XG4gICAgfVxuICAgIHJldHVybiBzYi5jb250ZW50cygpO1xuICB9XG5cbiAgZ2V0SW50ZXJ2YWwoKSB7XG4gICAgY29uc3QgcG9zID0gdGhpcy5nZXRSaWdodG1vc3RGYWlsdXJlUG9zaXRpb24oKTtcbiAgICByZXR1cm4gbmV3IEludGVydmFsKHRoaXMuaW5wdXQsIHBvcywgcG9zKTtcbiAgfVxufVxuIiwiZXhwb3J0IGNsYXNzIFBvc0luZm8ge1xuICBjb25zdHJ1Y3RvcigpIHtcbiAgICB0aGlzLmFwcGxpY2F0aW9uTWVtb0tleVN0YWNrID0gW107IC8vIGFjdGl2ZSBhcHBsaWNhdGlvbnMgYXQgdGhpcyBwb3NpdGlvblxuICAgIHRoaXMubWVtbyA9IHt9O1xuICAgIHRoaXMubWF4RXhhbWluZWRMZW5ndGggPSAwO1xuICAgIHRoaXMubWF4UmlnaHRtb3N0RmFpbHVyZU9mZnNldCA9IC0xO1xuICAgIHRoaXMuY3VycmVudExlZnRSZWN1cnNpb24gPSB1bmRlZmluZWQ7XG4gIH1cblxuICBpc0FjdGl2ZShhcHBsaWNhdGlvbikge1xuICAgIHJldHVybiB0aGlzLmFwcGxpY2F0aW9uTWVtb0tleVN0YWNrLmluZGV4T2YoYXBwbGljYXRpb24udG9NZW1vS2V5KCkpID49IDA7XG4gIH1cblxuICBlbnRlcihhcHBsaWNhdGlvbikge1xuICAgIHRoaXMuYXBwbGljYXRpb25NZW1vS2V5U3RhY2sucHVzaChhcHBsaWNhdGlvbi50b01lbW9LZXkoKSk7XG4gIH1cblxuICBleGl0KCkge1xuICAgIHRoaXMuYXBwbGljYXRpb25NZW1vS2V5U3RhY2sucG9wKCk7XG4gIH1cblxuICBzdGFydExlZnRSZWN1cnNpb24oaGVhZEFwcGxpY2F0aW9uLCBtZW1vUmVjKSB7XG4gICAgbWVtb1JlYy5pc0xlZnRSZWN1cnNpb24gPSB0cnVlO1xuICAgIG1lbW9SZWMuaGVhZEFwcGxpY2F0aW9uID0gaGVhZEFwcGxpY2F0aW9uO1xuICAgIG1lbW9SZWMubmV4dExlZnRSZWN1cnNpb24gPSB0aGlzLmN1cnJlbnRMZWZ0UmVjdXJzaW9uO1xuICAgIHRoaXMuY3VycmVudExlZnRSZWN1cnNpb24gPSBtZW1vUmVjO1xuXG4gICAgY29uc3Qge2FwcGxpY2F0aW9uTWVtb0tleVN0YWNrfSA9IHRoaXM7XG4gICAgY29uc3QgaW5kZXhPZkZpcnN0SW52b2x2ZWRSdWxlID1cbiAgICAgIGFwcGxpY2F0aW9uTWVtb0tleVN0YWNrLmluZGV4T2YoaGVhZEFwcGxpY2F0aW9uLnRvTWVtb0tleSgpKSArIDE7XG4gICAgY29uc3QgaW52b2x2ZWRBcHBsaWNhdGlvbk1lbW9LZXlzID0gYXBwbGljYXRpb25NZW1vS2V5U3RhY2suc2xpY2UoXG4gICAgICBpbmRleE9mRmlyc3RJbnZvbHZlZFJ1bGVcbiAgICApO1xuXG4gICAgbWVtb1JlYy5pc0ludm9sdmVkID0gZnVuY3Rpb24gKGFwcGxpY2F0aW9uTWVtb0tleSkge1xuICAgICAgcmV0dXJuIGludm9sdmVkQXBwbGljYXRpb25NZW1vS2V5cy5pbmRleE9mKGFwcGxpY2F0aW9uTWVtb0tleSkgPj0gMDtcbiAgICB9O1xuXG4gICAgbWVtb1JlYy51cGRhdGVJbnZvbHZlZEFwcGxpY2F0aW9uTWVtb0tleXMgPSBmdW5jdGlvbiAoKSB7XG4gICAgICBmb3IgKGxldCBpZHggPSBpbmRleE9mRmlyc3RJbnZvbHZlZFJ1bGU7IGlkeCA8IGFwcGxpY2F0aW9uTWVtb0tleVN0YWNrLmxlbmd0aDsgaWR4KyspIHtcbiAgICAgICAgY29uc3QgYXBwbGljYXRpb25NZW1vS2V5ID0gYXBwbGljYXRpb25NZW1vS2V5U3RhY2tbaWR4XTtcbiAgICAgICAgaWYgKCF0aGlzLmlzSW52b2x2ZWQoYXBwbGljYXRpb25NZW1vS2V5KSkge1xuICAgICAgICAgIGludm9sdmVkQXBwbGljYXRpb25NZW1vS2V5cy5wdXNoKGFwcGxpY2F0aW9uTWVtb0tleSk7XG4gICAgICAgIH1cbiAgICAgIH1cbiAgICB9O1xuICB9XG5cbiAgZW5kTGVmdFJlY3Vyc2lvbigpIHtcbiAgICB0aGlzLmN1cnJlbnRMZWZ0UmVjdXJzaW9uID0gdGhpcy5jdXJyZW50TGVmdFJlY3Vyc2lvbi5uZXh0TGVmdFJlY3Vyc2lvbjtcbiAgfVxuXG4gIC8vIE5vdGU6IHRoaXMgbWV0aG9kIGRvZXNuJ3QgZ2V0IGNhbGxlZCBmb3IgdGhlIFwiaGVhZFwiIG9mIGEgbGVmdCByZWN1cnNpb24gLS0gZm9yIExSIGhlYWRzLFxuICAvLyB0aGUgbWVtb2l6ZWQgcmVzdWx0ICh3aGljaCBzdGFydHMgb3V0IGJlaW5nIGEgZmFpbHVyZSkgaXMgYWx3YXlzIHVzZWQuXG4gIHNob3VsZFVzZU1lbW9pemVkUmVzdWx0KG1lbW9SZWMpIHtcbiAgICBpZiAoIW1lbW9SZWMuaXNMZWZ0UmVjdXJzaW9uKSB7XG4gICAgICByZXR1cm4gdHJ1ZTtcbiAgICB9XG4gICAgY29uc3Qge2FwcGxpY2F0aW9uTWVtb0tleVN0YWNrfSA9IHRoaXM7XG4gICAgZm9yIChsZXQgaWR4ID0gMDsgaWR4IDwgYXBwbGljYXRpb25NZW1vS2V5U3RhY2subGVuZ3RoOyBpZHgrKykge1xuICAgICAgY29uc3QgYXBwbGljYXRpb25NZW1vS2V5ID0gYXBwbGljYXRpb25NZW1vS2V5U3RhY2tbaWR4XTtcbiAgICAgIGlmIChtZW1vUmVjLmlzSW52b2x2ZWQoYXBwbGljYXRpb25NZW1vS2V5KSkge1xuICAgICAgICByZXR1cm4gZmFsc2U7XG4gICAgICB9XG4gICAgfVxuICAgIHJldHVybiB0cnVlO1xuICB9XG5cbiAgbWVtb2l6ZShtZW1vS2V5LCBtZW1vUmVjKSB7XG4gICAgdGhpcy5tZW1vW21lbW9LZXldID0gbWVtb1JlYztcbiAgICB0aGlzLm1heEV4YW1pbmVkTGVuZ3RoID0gTWF0aC5tYXgodGhpcy5tYXhFeGFtaW5lZExlbmd0aCwgbWVtb1JlYy5leGFtaW5lZExlbmd0aCk7XG4gICAgdGhpcy5tYXhSaWdodG1vc3RGYWlsdXJlT2Zmc2V0ID0gTWF0aC5tYXgoXG4gICAgICB0aGlzLm1heFJpZ2h0bW9zdEZhaWx1cmVPZmZzZXQsXG4gICAgICBtZW1vUmVjLnJpZ2h0bW9zdEZhaWx1cmVPZmZzZXRcbiAgICApO1xuICAgIHJldHVybiBtZW1vUmVjO1xuICB9XG5cbiAgY2xlYXJPYnNvbGV0ZUVudHJpZXMocG9zLCBpbnZhbGlkYXRlZElkeCkge1xuICAgIGlmIChwb3MgKyB0aGlzLm1heEV4YW1pbmVkTGVuZ3RoIDw9IGludmFsaWRhdGVkSWR4KSB7XG4gICAgICAvLyBPcHRpbWl6YXRpb246IG5vbmUgb2YgdGhlIHJ1bGUgYXBwbGljYXRpb25zIHRoYXQgd2VyZSBtZW1vaXplZCBoZXJlIGV4YW1pbmVkIHRoZVxuICAgICAgLy8gaW50ZXJ2YWwgb2YgdGhlIGlucHV0IHRoYXQgY2hhbmdlZCwgc28gbm90aGluZyBoYXMgdG8gYmUgaW52YWxpZGF0ZWQuXG4gICAgICByZXR1cm47XG4gICAgfVxuXG4gICAgY29uc3Qge21lbW99ID0gdGhpcztcbiAgICB0aGlzLm1heEV4YW1pbmVkTGVuZ3RoID0gMDtcbiAgICB0aGlzLm1heFJpZ2h0bW9zdEZhaWx1cmVPZmZzZXQgPSAtMTtcbiAgICBPYmplY3Qua2V5cyhtZW1vKS5mb3JFYWNoKGsgPT4ge1xuICAgICAgY29uc3QgbWVtb1JlYyA9IG1lbW9ba107XG4gICAgICBpZiAocG9zICsgbWVtb1JlYy5leGFtaW5lZExlbmd0aCA+IGludmFsaWRhdGVkSWR4KSB7XG4gICAgICAgIGRlbGV0ZSBtZW1vW2tdO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgdGhpcy5tYXhFeGFtaW5lZExlbmd0aCA9IE1hdGgubWF4KHRoaXMubWF4RXhhbWluZWRMZW5ndGgsIG1lbW9SZWMuZXhhbWluZWRMZW5ndGgpO1xuICAgICAgICB0aGlzLm1heFJpZ2h0bW9zdEZhaWx1cmVPZmZzZXQgPSBNYXRoLm1heChcbiAgICAgICAgICB0aGlzLm1heFJpZ2h0bW9zdEZhaWx1cmVPZmZzZXQsXG4gICAgICAgICAgbWVtb1JlYy5yaWdodG1vc3RGYWlsdXJlT2Zmc2V0XG4gICAgICAgICk7XG4gICAgICB9XG4gICAgfSk7XG4gIH1cbn1cbiIsImltcG9ydCB7SW50ZXJ2YWx9IGZyb20gJy4vSW50ZXJ2YWwuanMnO1xuaW1wb3J0ICogYXMgY29tbW9uIGZyb20gJy4vY29tbW9uLmpzJztcblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cbi8vIFByaXZhdGUgc3R1ZmZcbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG5cbi8vIFVuaWNvZGUgY2hhcmFjdGVycyB0aGF0IGFyZSB1c2VkIGluIHRoZSBgdG9TdHJpbmdgIG91dHB1dC5cbmNvbnN0IEJBTExPVF9YID0gJ1xcdTI3MTcnO1xuY29uc3QgQ0hFQ0tfTUFSSyA9ICdcXHUyNzEzJztcbmNvbnN0IERPVF9PUEVSQVRPUiA9ICdcXHUyMkM1JztcbmNvbnN0IFJJR0hUV0FSRFNfRE9VQkxFX0FSUk9XID0gJ1xcdTIxRDInO1xuY29uc3QgU1lNQk9MX0ZPUl9IT1JJWk9OVEFMX1RBQlVMQVRJT04gPSAnXFx1MjQwOSc7XG5jb25zdCBTWU1CT0xfRk9SX0xJTkVfRkVFRCA9ICdcXHUyNDBBJztcbmNvbnN0IFNZTUJPTF9GT1JfQ0FSUklBR0VfUkVUVVJOID0gJ1xcdTI0MEQnO1xuXG5jb25zdCBGbGFncyA9IHtcbiAgc3VjY2VlZGVkOiAxIDw8IDAsXG4gIGlzUm9vdE5vZGU6IDEgPDwgMSxcbiAgaXNJbXBsaWNpdFNwYWNlczogMSA8PCAyLFxuICBpc01lbW9pemVkOiAxIDw8IDMsXG4gIGlzSGVhZE9mTGVmdFJlY3Vyc2lvbjogMSA8PCA0LFxuICB0ZXJtaW5hdGVzTFI6IDEgPDwgNSxcbn07XG5cbmZ1bmN0aW9uIHNwYWNlcyhuKSB7XG4gIHJldHVybiBjb21tb24ucmVwZWF0KCcgJywgbikuam9pbignJyk7XG59XG5cbi8vIFJldHVybiBhIHN0cmluZyByZXByZXNlbnRhdGlvbiBvZiBhIHBvcnRpb24gb2YgYGlucHV0YCBhdCBvZmZzZXQgYHBvc2AuXG4vLyBUaGUgcmVzdWx0IHdpbGwgY29udGFpbiBleGFjdGx5IGBsZW5gIGNoYXJhY3RlcnMuXG5mdW5jdGlvbiBnZXRJbnB1dEV4Y2VycHQoaW5wdXQsIHBvcywgbGVuKSB7XG4gIGNvbnN0IGV4Y2VycHQgPSBhc0VzY2FwZWRTdHJpbmcoaW5wdXQuc2xpY2UocG9zLCBwb3MgKyBsZW4pKTtcblxuICAvLyBQYWQgdGhlIG91dHB1dCBpZiBuZWNlc3NhcnkuXG4gIGlmIChleGNlcnB0Lmxlbmd0aCA8IGxlbikge1xuICAgIHJldHVybiBleGNlcnB0ICsgY29tbW9uLnJlcGVhdCgnICcsIGxlbiAtIGV4Y2VycHQubGVuZ3RoKS5qb2luKCcnKTtcbiAgfVxuICByZXR1cm4gZXhjZXJwdDtcbn1cblxuZnVuY3Rpb24gYXNFc2NhcGVkU3RyaW5nKG9iaikge1xuICBpZiAodHlwZW9mIG9iaiA9PT0gJ3N0cmluZycpIHtcbiAgICAvLyBSZXBsYWNlIG5vbi1wcmludGFibGUgY2hhcmFjdGVycyB3aXRoIHZpc2libGUgc3ltYm9scy5cbiAgICByZXR1cm4gb2JqXG4gICAgICAucmVwbGFjZSgvIC9nLCBET1RfT1BFUkFUT1IpXG4gICAgICAucmVwbGFjZSgvXFx0L2csIFNZTUJPTF9GT1JfSE9SSVpPTlRBTF9UQUJVTEFUSU9OKVxuICAgICAgLnJlcGxhY2UoL1xcbi9nLCBTWU1CT0xfRk9SX0xJTkVfRkVFRClcbiAgICAgIC5yZXBsYWNlKC9cXHIvZywgU1lNQk9MX0ZPUl9DQVJSSUFHRV9SRVRVUk4pO1xuICB9XG4gIHJldHVybiBTdHJpbmcob2JqKTtcbn1cblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0gVHJhY2UgLS0tLS0tLS0tLS0tLS0tLS1cblxuZXhwb3J0IGNsYXNzIFRyYWNlIHtcbiAgY29uc3RydWN0b3IoaW5wdXQsIHBvczEsIHBvczIsIGV4cHIsIHN1Y2NlZWRlZCwgYmluZGluZ3MsIG9wdENoaWxkcmVuKSB7XG4gICAgdGhpcy5pbnB1dCA9IGlucHV0O1xuICAgIHRoaXMucG9zID0gdGhpcy5wb3MxID0gcG9zMTtcbiAgICB0aGlzLnBvczIgPSBwb3MyO1xuICAgIHRoaXMuc291cmNlID0gbmV3IEludGVydmFsKGlucHV0LCBwb3MxLCBwb3MyKTtcbiAgICB0aGlzLmV4cHIgPSBleHByO1xuICAgIHRoaXMuYmluZGluZ3MgPSBiaW5kaW5ncztcbiAgICB0aGlzLmNoaWxkcmVuID0gb3B0Q2hpbGRyZW4gfHwgW107XG4gICAgdGhpcy50ZXJtaW5hdGluZ0xSRW50cnkgPSBudWxsO1xuXG4gICAgdGhpcy5fZmxhZ3MgPSBzdWNjZWVkZWQgPyBGbGFncy5zdWNjZWVkZWQgOiAwO1xuICB9XG5cbiAgZ2V0IGRpc3BsYXlTdHJpbmcoKSB7XG4gICAgcmV0dXJuIHRoaXMuZXhwci50b0Rpc3BsYXlTdHJpbmcoKTtcbiAgfVxuXG4gIGNsb25lKCkge1xuICAgIHJldHVybiB0aGlzLmNsb25lV2l0aEV4cHIodGhpcy5leHByKTtcbiAgfVxuXG4gIGNsb25lV2l0aEV4cHIoZXhwcikge1xuICAgIGNvbnN0IGFucyA9IG5ldyBUcmFjZShcbiAgICAgIHRoaXMuaW5wdXQsXG4gICAgICB0aGlzLnBvcyxcbiAgICAgIHRoaXMucG9zMixcbiAgICAgIGV4cHIsXG4gICAgICB0aGlzLnN1Y2NlZWRlZCxcbiAgICAgIHRoaXMuYmluZGluZ3MsXG4gICAgICB0aGlzLmNoaWxkcmVuXG4gICAgKTtcblxuICAgIGFucy5pc0hlYWRPZkxlZnRSZWN1cnNpb24gPSB0aGlzLmlzSGVhZE9mTGVmdFJlY3Vyc2lvbjtcbiAgICBhbnMuaXNJbXBsaWNpdFNwYWNlcyA9IHRoaXMuaXNJbXBsaWNpdFNwYWNlcztcbiAgICBhbnMuaXNNZW1vaXplZCA9IHRoaXMuaXNNZW1vaXplZDtcbiAgICBhbnMuaXNSb290Tm9kZSA9IHRoaXMuaXNSb290Tm9kZTtcbiAgICBhbnMudGVybWluYXRlc0xSID0gdGhpcy50ZXJtaW5hdGVzTFI7XG4gICAgYW5zLnRlcm1pbmF0aW5nTFJFbnRyeSA9IHRoaXMudGVybWluYXRpbmdMUkVudHJ5O1xuICAgIHJldHVybiBhbnM7XG4gIH1cblxuICAvLyBSZWNvcmQgdGhlIHRyYWNlIGluZm9ybWF0aW9uIGZvciB0aGUgdGVybWluYXRpbmcgY29uZGl0aW9uIG9mIHRoZSBMUiBsb29wLlxuICByZWNvcmRMUlRlcm1pbmF0aW9uKHJ1bGVCb2R5VHJhY2UsIHZhbHVlKSB7XG4gICAgdGhpcy50ZXJtaW5hdGluZ0xSRW50cnkgPSBuZXcgVHJhY2UoXG4gICAgICB0aGlzLmlucHV0LFxuICAgICAgdGhpcy5wb3MsXG4gICAgICB0aGlzLnBvczIsXG4gICAgICB0aGlzLmV4cHIsXG4gICAgICBmYWxzZSxcbiAgICAgIFt2YWx1ZV0sXG4gICAgICBbcnVsZUJvZHlUcmFjZV1cbiAgICApO1xuICAgIHRoaXMudGVybWluYXRpbmdMUkVudHJ5LnRlcm1pbmF0ZXNMUiA9IHRydWU7XG4gIH1cblxuICAvLyBSZWN1cnNpdmVseSB0cmF2ZXJzZSB0aGlzIHRyYWNlIG5vZGUgYW5kIGFsbCBpdHMgZGVzY2VuZGVudHMsIGNhbGxpbmcgYSB2aXNpdG9yIGZ1bmN0aW9uXG4gIC8vIGZvciBlYWNoIG5vZGUgdGhhdCBpcyB2aXNpdGVkLiBJZiBgdmlzdG9yT2JqT3JGbmAgaXMgYW4gb2JqZWN0LCB0aGVuIGl0cyAnZW50ZXInIHByb3BlcnR5XG4gIC8vIGlzIGEgZnVuY3Rpb24gdG8gY2FsbCBiZWZvcmUgdmlzaXRpbmcgdGhlIGNoaWxkcmVuIG9mIGEgbm9kZSwgYW5kIGl0cyAnZXhpdCcgcHJvcGVydHkgaXNcbiAgLy8gYSBmdW5jdGlvbiB0byBjYWxsIGFmdGVyd2FyZHMuIElmIGB2aXNpdG9yT2JqT3JGbmAgaXMgYSBmdW5jdGlvbiwgaXQgcmVwcmVzZW50cyB0aGUgJ2VudGVyJ1xuICAvLyBmdW5jdGlvbi5cbiAgLy9cbiAgLy8gVGhlIGZ1bmN0aW9ucyBhcmUgY2FsbGVkIHdpdGggdGhyZWUgYXJndW1lbnRzOiB0aGUgVHJhY2Ugbm9kZSwgaXRzIHBhcmVudCBUcmFjZSwgYW5kIGEgbnVtYmVyXG4gIC8vIHJlcHJlc2VudGluZyB0aGUgZGVwdGggb2YgdGhlIG5vZGUgaW4gdGhlIHRyZWUuIChUaGUgcm9vdCBub2RlIGhhcyBkZXB0aCAwLikgYG9wdFRoaXNBcmdgLCBpZlxuICAvLyBzcGVjaWZpZWQsIGlzIHRoZSB2YWx1ZSB0byB1c2UgZm9yIGB0aGlzYCB3aGVuIGV4ZWN1dGluZyB0aGUgdmlzaXRvciBmdW5jdGlvbnMuXG4gIHdhbGsodmlzaXRvck9iak9yRm4sIG9wdFRoaXNBcmcpIHtcbiAgICBsZXQgdmlzaXRvciA9IHZpc2l0b3JPYmpPckZuO1xuICAgIGlmICh0eXBlb2YgdmlzaXRvciA9PT0gJ2Z1bmN0aW9uJykge1xuICAgICAgdmlzaXRvciA9IHtlbnRlcjogdmlzaXRvcn07XG4gICAgfVxuXG4gICAgZnVuY3Rpb24gX3dhbGsobm9kZSwgcGFyZW50LCBkZXB0aCkge1xuICAgICAgbGV0IHJlY3Vyc2UgPSB0cnVlO1xuICAgICAgaWYgKHZpc2l0b3IuZW50ZXIpIHtcbiAgICAgICAgaWYgKHZpc2l0b3IuZW50ZXIuY2FsbChvcHRUaGlzQXJnLCBub2RlLCBwYXJlbnQsIGRlcHRoKSA9PT0gVHJhY2UucHJvdG90eXBlLlNLSVApIHtcbiAgICAgICAgICByZWN1cnNlID0gZmFsc2U7XG4gICAgICAgIH1cbiAgICAgIH1cbiAgICAgIGlmIChyZWN1cnNlKSB7XG4gICAgICAgIG5vZGUuY2hpbGRyZW4uZm9yRWFjaChjaGlsZCA9PiB7XG4gICAgICAgICAgX3dhbGsoY2hpbGQsIG5vZGUsIGRlcHRoICsgMSk7XG4gICAgICAgIH0pO1xuICAgICAgICBpZiAodmlzaXRvci5leGl0KSB7XG4gICAgICAgICAgdmlzaXRvci5leGl0LmNhbGwob3B0VGhpc0FyZywgbm9kZSwgcGFyZW50LCBkZXB0aCk7XG4gICAgICAgIH1cbiAgICAgIH1cbiAgICB9XG4gICAgaWYgKHRoaXMuaXNSb290Tm9kZSkge1xuICAgICAgLy8gRG9uJ3QgdmlzaXQgdGhlIHJvb3Qgbm9kZSBpdHNlbGYsIG9ubHkgaXRzIGNoaWxkcmVuLlxuICAgICAgdGhpcy5jaGlsZHJlbi5mb3JFYWNoKGMgPT4ge1xuICAgICAgICBfd2FsayhjLCBudWxsLCAwKTtcbiAgICAgIH0pO1xuICAgIH0gZWxzZSB7XG4gICAgICBfd2Fsayh0aGlzLCBudWxsLCAwKTtcbiAgICB9XG4gIH1cblxuICAvLyBSZXR1cm4gYSBzdHJpbmcgcmVwcmVzZW50YXRpb24gb2YgdGhlIHRyYWNlLlxuICAvLyBTYW1wbGU6XG4gIC8vICAgICAxMuKLhSvii4Uy4ouFKuKLhTMg4pyTIGV4cCDih5IgIFwiMTJcIlxuICAvLyAgICAgMTLii4Ur4ouFMuKLhSrii4UzICAg4pyTIGFkZEV4cCAoTFIpIOKHkiAgXCIxMlwiXG4gIC8vICAgICAxMuKLhSvii4Uy4ouFKuKLhTMgICAgICAg4pyXIGFkZEV4cF9wbHVzXG4gIHRvU3RyaW5nKCkge1xuICAgIGNvbnN0IHNiID0gbmV3IGNvbW1vbi5TdHJpbmdCdWZmZXIoKTtcbiAgICB0aGlzLndhbGsoKG5vZGUsIHBhcmVudCwgZGVwdGgpID0+IHtcbiAgICAgIGlmICghbm9kZSkge1xuICAgICAgICByZXR1cm4gdGhpcy5TS0lQO1xuICAgICAgfVxuICAgICAgY29uc3QgY3Rvck5hbWUgPSBub2RlLmV4cHIuY29uc3RydWN0b3IubmFtZTtcbiAgICAgIC8vIERvbid0IHByaW50IGFueXRoaW5nIGZvciBBbHQgbm9kZXMuXG4gICAgICBpZiAoY3Rvck5hbWUgPT09ICdBbHQnKSB7XG4gICAgICAgIHJldHVybjtcbiAgICAgIH1cbiAgICAgIHNiLmFwcGVuZChnZXRJbnB1dEV4Y2VycHQobm9kZS5pbnB1dCwgbm9kZS5wb3MsIDEwKSArIHNwYWNlcyhkZXB0aCAqIDIgKyAxKSk7XG4gICAgICBzYi5hcHBlbmQoKG5vZGUuc3VjY2VlZGVkID8gQ0hFQ0tfTUFSSyA6IEJBTExPVF9YKSArICcgJyArIG5vZGUuZGlzcGxheVN0cmluZyk7XG4gICAgICBpZiAobm9kZS5pc0hlYWRPZkxlZnRSZWN1cnNpb24pIHtcbiAgICAgICAgc2IuYXBwZW5kKCcgKExSKScpO1xuICAgICAgfVxuICAgICAgaWYgKG5vZGUuc3VjY2VlZGVkKSB7XG4gICAgICAgIGNvbnN0IGNvbnRlbnRzID0gYXNFc2NhcGVkU3RyaW5nKG5vZGUuc291cmNlLmNvbnRlbnRzKTtcbiAgICAgICAgc2IuYXBwZW5kKCcgJyArIFJJR0hUV0FSRFNfRE9VQkxFX0FSUk9XICsgJyAgJyk7XG4gICAgICAgIHNiLmFwcGVuZCh0eXBlb2YgY29udGVudHMgPT09ICdzdHJpbmcnID8gJ1wiJyArIGNvbnRlbnRzICsgJ1wiJyA6IGNvbnRlbnRzKTtcbiAgICAgIH1cbiAgICAgIHNiLmFwcGVuZCgnXFxuJyk7XG4gICAgfSk7XG4gICAgcmV0dXJuIHNiLmNvbnRlbnRzKCk7XG4gIH1cbn1cblxuLy8gQSB2YWx1ZSB0aGF0IGNhbiBiZSByZXR1cm5lZCBmcm9tIHZpc2l0b3IgZnVuY3Rpb25zIHRvIGluZGljYXRlIHRoYXQgYVxuLy8gbm9kZSBzaG91bGQgbm90IGJlIHJlY3Vyc2VkIGludG8uXG5UcmFjZS5wcm90b3R5cGUuU0tJUCA9IHt9O1xuXG4vLyBGb3IgY29udmVuaWVuY2UsIGNyZWF0ZSBhIGdldHRlciBhbmQgc2V0dGVyIGZvciB0aGUgYm9vbGVhbiBmbGFncyBpbiBgRmxhZ3NgLlxuT2JqZWN0LmtleXMoRmxhZ3MpLmZvckVhY2gobmFtZSA9PiB7XG4gIGNvbnN0IG1hc2sgPSBGbGFnc1tuYW1lXTtcbiAgT2JqZWN0LmRlZmluZVByb3BlcnR5KFRyYWNlLnByb3RvdHlwZSwgbmFtZSwge1xuICAgIGdldCgpIHtcbiAgICAgIHJldHVybiAodGhpcy5fZmxhZ3MgJiBtYXNrKSAhPT0gMDtcbiAgICB9LFxuICAgIHNldCh2YWwpIHtcbiAgICAgIGlmICh2YWwpIHtcbiAgICAgICAgdGhpcy5fZmxhZ3MgfD0gbWFzaztcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHRoaXMuX2ZsYWdzICY9IH5tYXNrO1xuICAgICAgfVxuICAgIH0sXG4gIH0pO1xufSk7XG4iLCJpbXBvcnQge2Fic3RyYWN0fSBmcm9tICcuL2NvbW1vbi5qcyc7XG5pbXBvcnQgKiBhcyBwZXhwcnMgZnJvbSAnLi9wZXhwcnMtbWFpbi5qcyc7XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG4vLyBPcGVyYXRpb25zXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuXG4vKlxuICBSZXR1cm4gdHJ1ZSBpZiB3ZSBzaG91bGQgc2tpcCBzcGFjZXMgcHJlY2VkaW5nIHRoaXMgZXhwcmVzc2lvbiBpbiBhIHN5bnRhY3RpYyBjb250ZXh0LlxuKi9cbnBleHBycy5QRXhwci5wcm90b3R5cGUuYWxsb3dzU2tpcHBpbmdQcmVjZWRpbmdTcGFjZSA9IGFic3RyYWN0KCdhbGxvd3NTa2lwcGluZ1ByZWNlZGluZ1NwYWNlJyk7XG5cbi8qXG4gIEdlbmVyYWxseSwgdGhlc2UgYXJlIGFsbCBmaXJzdC1vcmRlciBleHByZXNzaW9ucyBhbmQgKHdpdGggdGhlIGV4Y2VwdGlvbiBvZiBBcHBseSlcbiAgZGlyZWN0bHkgcmVhZCBmcm9tIHRoZSBpbnB1dCBzdHJlYW0uXG4qL1xucGV4cHJzLmFueS5hbGxvd3NTa2lwcGluZ1ByZWNlZGluZ1NwYWNlID1cbiAgcGV4cHJzLmVuZC5hbGxvd3NTa2lwcGluZ1ByZWNlZGluZ1NwYWNlID1cbiAgcGV4cHJzLkFwcGx5LnByb3RvdHlwZS5hbGxvd3NTa2lwcGluZ1ByZWNlZGluZ1NwYWNlID1cbiAgcGV4cHJzLlRlcm1pbmFsLnByb3RvdHlwZS5hbGxvd3NTa2lwcGluZ1ByZWNlZGluZ1NwYWNlID1cbiAgcGV4cHJzLlJhbmdlLnByb3RvdHlwZS5hbGxvd3NTa2lwcGluZ1ByZWNlZGluZ1NwYWNlID1cbiAgcGV4cHJzLlVuaWNvZGVDaGFyLnByb3RvdHlwZS5hbGxvd3NTa2lwcGluZ1ByZWNlZGluZ1NwYWNlID1cbiAgICBmdW5jdGlvbiAoKSB7XG4gICAgICByZXR1cm4gdHJ1ZTtcbiAgICB9O1xuXG4vKlxuICBIaWdoZXItb3JkZXIgZXhwcmVzc2lvbnMgdGhhdCBkb24ndCBkaXJlY3RseSBjb25zdW1lIGlucHV0LlxuKi9cbnBleHBycy5BbHQucHJvdG90eXBlLmFsbG93c1NraXBwaW5nUHJlY2VkaW5nU3BhY2UgPVxuICBwZXhwcnMuSXRlci5wcm90b3R5cGUuYWxsb3dzU2tpcHBpbmdQcmVjZWRpbmdTcGFjZSA9XG4gIHBleHBycy5MZXgucHJvdG90eXBlLmFsbG93c1NraXBwaW5nUHJlY2VkaW5nU3BhY2UgPVxuICBwZXhwcnMuTG9va2FoZWFkLnByb3RvdHlwZS5hbGxvd3NTa2lwcGluZ1ByZWNlZGluZ1NwYWNlID1cbiAgcGV4cHJzLk5vdC5wcm90b3R5cGUuYWxsb3dzU2tpcHBpbmdQcmVjZWRpbmdTcGFjZSA9XG4gIHBleHBycy5QYXJhbS5wcm90b3R5cGUuYWxsb3dzU2tpcHBpbmdQcmVjZWRpbmdTcGFjZSA9XG4gIHBleHBycy5TZXEucHJvdG90eXBlLmFsbG93c1NraXBwaW5nUHJlY2VkaW5nU3BhY2UgPVxuICAgIGZ1bmN0aW9uICgpIHtcbiAgICAgIHJldHVybiBmYWxzZTtcbiAgICB9O1xuIiwiaW1wb3J0IHthYnN0cmFjdCwgaXNTeW50YWN0aWN9IGZyb20gJy4vY29tbW9uLmpzJztcbmltcG9ydCAqIGFzIGVycm9ycyBmcm9tICcuL2Vycm9ycy5qcyc7XG5pbXBvcnQgKiBhcyBwZXhwcnMgZnJvbSAnLi9wZXhwcnMtbWFpbi5qcyc7XG5pbXBvcnQgKiBhcyB1dGlsIGZyb20gJy4vdXRpbC5qcyc7XG5cbmxldCBCdWlsdEluUnVsZXM7XG5cbnV0aWwuYXdhaXRCdWlsdEluUnVsZXMoZyA9PiB7XG4gIEJ1aWx0SW5SdWxlcyA9IGc7XG59KTtcblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cbi8vIE9wZXJhdGlvbnNcbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG5cbmxldCBsZXhpZnlDb3VudDtcblxucGV4cHJzLlBFeHByLnByb3RvdHlwZS5hc3NlcnRBbGxBcHBsaWNhdGlvbnNBcmVWYWxpZCA9IGZ1bmN0aW9uIChydWxlTmFtZSwgZ3JhbW1hcikge1xuICBsZXhpZnlDb3VudCA9IDA7XG4gIHRoaXMuX2Fzc2VydEFsbEFwcGxpY2F0aW9uc0FyZVZhbGlkKHJ1bGVOYW1lLCBncmFtbWFyKTtcbn07XG5cbnBleHBycy5QRXhwci5wcm90b3R5cGUuX2Fzc2VydEFsbEFwcGxpY2F0aW9uc0FyZVZhbGlkID0gYWJzdHJhY3QoXG4gICdfYXNzZXJ0QWxsQXBwbGljYXRpb25zQXJlVmFsaWQnXG4pO1xuXG5wZXhwcnMuYW55Ll9hc3NlcnRBbGxBcHBsaWNhdGlvbnNBcmVWYWxpZCA9XG4gIHBleHBycy5lbmQuX2Fzc2VydEFsbEFwcGxpY2F0aW9uc0FyZVZhbGlkID1cbiAgcGV4cHJzLlRlcm1pbmFsLnByb3RvdHlwZS5fYXNzZXJ0QWxsQXBwbGljYXRpb25zQXJlVmFsaWQgPVxuICBwZXhwcnMuUmFuZ2UucHJvdG90eXBlLl9hc3NlcnRBbGxBcHBsaWNhdGlvbnNBcmVWYWxpZCA9XG4gIHBleHBycy5QYXJhbS5wcm90b3R5cGUuX2Fzc2VydEFsbEFwcGxpY2F0aW9uc0FyZVZhbGlkID1cbiAgcGV4cHJzLlVuaWNvZGVDaGFyLnByb3RvdHlwZS5fYXNzZXJ0QWxsQXBwbGljYXRpb25zQXJlVmFsaWQgPVxuICAgIGZ1bmN0aW9uIChydWxlTmFtZSwgZ3JhbW1hcikge1xuICAgICAgLy8gbm8tb3BcbiAgICB9O1xuXG5wZXhwcnMuTGV4LnByb3RvdHlwZS5fYXNzZXJ0QWxsQXBwbGljYXRpb25zQXJlVmFsaWQgPSBmdW5jdGlvbiAocnVsZU5hbWUsIGdyYW1tYXIpIHtcbiAgbGV4aWZ5Q291bnQrKztcbiAgdGhpcy5leHByLl9hc3NlcnRBbGxBcHBsaWNhdGlvbnNBcmVWYWxpZChydWxlTmFtZSwgZ3JhbW1hcik7XG4gIGxleGlmeUNvdW50LS07XG59O1xuXG5wZXhwcnMuQWx0LnByb3RvdHlwZS5fYXNzZXJ0QWxsQXBwbGljYXRpb25zQXJlVmFsaWQgPSBmdW5jdGlvbiAocnVsZU5hbWUsIGdyYW1tYXIpIHtcbiAgZm9yIChsZXQgaWR4ID0gMDsgaWR4IDwgdGhpcy50ZXJtcy5sZW5ndGg7IGlkeCsrKSB7XG4gICAgdGhpcy50ZXJtc1tpZHhdLl9hc3NlcnRBbGxBcHBsaWNhdGlvbnNBcmVWYWxpZChydWxlTmFtZSwgZ3JhbW1hcik7XG4gIH1cbn07XG5cbnBleHBycy5TZXEucHJvdG90eXBlLl9hc3NlcnRBbGxBcHBsaWNhdGlvbnNBcmVWYWxpZCA9IGZ1bmN0aW9uIChydWxlTmFtZSwgZ3JhbW1hcikge1xuICBmb3IgKGxldCBpZHggPSAwOyBpZHggPCB0aGlzLmZhY3RvcnMubGVuZ3RoOyBpZHgrKykge1xuICAgIHRoaXMuZmFjdG9yc1tpZHhdLl9hc3NlcnRBbGxBcHBsaWNhdGlvbnNBcmVWYWxpZChydWxlTmFtZSwgZ3JhbW1hcik7XG4gIH1cbn07XG5cbnBleHBycy5JdGVyLnByb3RvdHlwZS5fYXNzZXJ0QWxsQXBwbGljYXRpb25zQXJlVmFsaWQgPVxuICBwZXhwcnMuTm90LnByb3RvdHlwZS5fYXNzZXJ0QWxsQXBwbGljYXRpb25zQXJlVmFsaWQgPVxuICBwZXhwcnMuTG9va2FoZWFkLnByb3RvdHlwZS5fYXNzZXJ0QWxsQXBwbGljYXRpb25zQXJlVmFsaWQgPVxuICAgIGZ1bmN0aW9uIChydWxlTmFtZSwgZ3JhbW1hcikge1xuICAgICAgdGhpcy5leHByLl9hc3NlcnRBbGxBcHBsaWNhdGlvbnNBcmVWYWxpZChydWxlTmFtZSwgZ3JhbW1hcik7XG4gICAgfTtcblxucGV4cHJzLkFwcGx5LnByb3RvdHlwZS5fYXNzZXJ0QWxsQXBwbGljYXRpb25zQXJlVmFsaWQgPSBmdW5jdGlvbiAoXG4gIHJ1bGVOYW1lLFxuICBncmFtbWFyLFxuICBza2lwU3ludGFjdGljQ2hlY2sgPSBmYWxzZVxuKSB7XG4gIGNvbnN0IHJ1bGVJbmZvID0gZ3JhbW1hci5ydWxlc1t0aGlzLnJ1bGVOYW1lXTtcbiAgY29uc3QgaXNDb250ZXh0U3ludGFjdGljID0gaXNTeW50YWN0aWMocnVsZU5hbWUpICYmIGxleGlmeUNvdW50ID09PSAwO1xuXG4gIC8vIE1ha2Ugc3VyZSB0aGF0IHRoZSBydWxlIGV4aXN0cy4uLlxuICBpZiAoIXJ1bGVJbmZvKSB7XG4gICAgdGhyb3cgZXJyb3JzLnVuZGVjbGFyZWRSdWxlKHRoaXMucnVsZU5hbWUsIGdyYW1tYXIubmFtZSwgdGhpcy5zb3VyY2UpO1xuICB9XG5cbiAgLy8gLi4uYW5kIHRoYXQgdGhpcyBhcHBsaWNhdGlvbiBpcyBhbGxvd2VkXG4gIGlmICghc2tpcFN5bnRhY3RpY0NoZWNrICYmIGlzU3ludGFjdGljKHRoaXMucnVsZU5hbWUpICYmICFpc0NvbnRleHRTeW50YWN0aWMpIHtcbiAgICB0aHJvdyBlcnJvcnMuYXBwbGljYXRpb25PZlN5bnRhY3RpY1J1bGVGcm9tTGV4aWNhbENvbnRleHQodGhpcy5ydWxlTmFtZSwgdGhpcyk7XG4gIH1cblxuICAvLyAuLi5hbmQgdGhhdCB0aGlzIGFwcGxpY2F0aW9uIGhhcyB0aGUgY29ycmVjdCBudW1iZXIgb2YgYXJndW1lbnRzLlxuICBjb25zdCBhY3R1YWwgPSB0aGlzLmFyZ3MubGVuZ3RoO1xuICBjb25zdCBleHBlY3RlZCA9IHJ1bGVJbmZvLmZvcm1hbHMubGVuZ3RoO1xuICBpZiAoYWN0dWFsICE9PSBleHBlY3RlZCkge1xuICAgIHRocm93IGVycm9ycy53cm9uZ051bWJlck9mQXJndW1lbnRzKHRoaXMucnVsZU5hbWUsIGV4cGVjdGVkLCBhY3R1YWwsIHRoaXMuc291cmNlKTtcbiAgfVxuXG4gIGNvbnN0IGlzQnVpbHRJbkFwcGx5U3ludGFjdGljID1cbiAgICBCdWlsdEluUnVsZXMgJiYgcnVsZUluZm8gPT09IEJ1aWx0SW5SdWxlcy5ydWxlcy5hcHBseVN5bnRhY3RpYztcbiAgY29uc3QgaXNCdWlsdEluQ2FzZUluc2Vuc2l0aXZlID1cbiAgICBCdWlsdEluUnVsZXMgJiYgcnVsZUluZm8gPT09IEJ1aWx0SW5SdWxlcy5ydWxlcy5jYXNlSW5zZW5zaXRpdmU7XG5cbiAgLy8gSWYgaXQncyBhbiBhcHBsaWNhdGlvbiBvZiAnY2FzZUluc2Vuc2l0aXZlJywgZW5zdXJlIHRoYXQgdGhlIGFyZ3VtZW50IGlzIGEgVGVybWluYWwuXG4gIGlmIChpc0J1aWx0SW5DYXNlSW5zZW5zaXRpdmUpIHtcbiAgICBpZiAoISh0aGlzLmFyZ3NbMF0gaW5zdGFuY2VvZiBwZXhwcnMuVGVybWluYWwpKSB7XG4gICAgICB0aHJvdyBlcnJvcnMuaW5jb3JyZWN0QXJndW1lbnRUeXBlKCdhIFRlcm1pbmFsIChlLmcuIFwiYWJjXCIpJywgdGhpcy5hcmdzWzBdKTtcbiAgICB9XG4gIH1cblxuICBpZiAoaXNCdWlsdEluQXBwbHlTeW50YWN0aWMpIHtcbiAgICBjb25zdCBhcmcgPSB0aGlzLmFyZ3NbMF07XG4gICAgaWYgKCEoYXJnIGluc3RhbmNlb2YgcGV4cHJzLkFwcGx5KSkge1xuICAgICAgdGhyb3cgZXJyb3JzLmluY29ycmVjdEFyZ3VtZW50VHlwZSgnYSBzeW50YWN0aWMgcnVsZSBhcHBsaWNhdGlvbicsIGFyZyk7XG4gICAgfVxuICAgIGlmICghaXNTeW50YWN0aWMoYXJnLnJ1bGVOYW1lKSkge1xuICAgICAgdGhyb3cgZXJyb3JzLmFwcGx5U3ludGFjdGljV2l0aExleGljYWxSdWxlQXBwbGljYXRpb24oYXJnKTtcbiAgICB9XG4gICAgaWYgKGlzQ29udGV4dFN5bnRhY3RpYykge1xuICAgICAgdGhyb3cgZXJyb3JzLnVubmVjZXNzYXJ5RXhwZXJpbWVudGFsQXBwbHlTeW50YWN0aWModGhpcyk7XG4gICAgfVxuICB9XG5cbiAgLy8gLi4uYW5kIHRoYXQgYWxsIG9mIHRoZSBhcmd1bWVudCBleHByZXNzaW9ucyBvbmx5IGhhdmUgdmFsaWQgYXBwbGljYXRpb25zIGFuZCBoYXZlIGFyaXR5IDEuXG4gIC8vIElmIGB0aGlzYCBpcyBhbiBhcHBsaWNhdGlvbiBvZiB0aGUgYnVpbHQtaW4gYXBwbHlTeW50YWN0aWMgcnVsZSwgdGhlbiBpdHMgYXJnIGlzXG4gIC8vIGFsbG93ZWQgKGFuZCBleHBlY3RlZCkgdG8gYmUgYSBzeW50YWN0aWMgcnVsZSwgZXZlbiBpZiB3ZSdyZSBpbiBhIGxleGljYWwgY29udGV4dC5cbiAgdGhpcy5hcmdzLmZvckVhY2goYXJnID0+IHtcbiAgICBhcmcuX2Fzc2VydEFsbEFwcGxpY2F0aW9uc0FyZVZhbGlkKHJ1bGVOYW1lLCBncmFtbWFyLCBpc0J1aWx0SW5BcHBseVN5bnRhY3RpYyk7XG4gICAgaWYgKGFyZy5nZXRBcml0eSgpICE9PSAxKSB7XG4gICAgICB0aHJvdyBlcnJvcnMuaW52YWxpZFBhcmFtZXRlcih0aGlzLnJ1bGVOYW1lLCBhcmcpO1xuICAgIH1cbiAgfSk7XG59O1xuIiwiaW1wb3J0IHthYnN0cmFjdH0gZnJvbSAnLi9jb21tb24uanMnO1xuaW1wb3J0ICogYXMgZXJyb3JzIGZyb20gJy4vZXJyb3JzLmpzJztcbmltcG9ydCAqIGFzIHBleHBycyBmcm9tICcuL3BleHBycy1tYWluLmpzJztcblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cbi8vIE9wZXJhdGlvbnNcbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG5cbnBleHBycy5QRXhwci5wcm90b3R5cGUuYXNzZXJ0Q2hvaWNlc0hhdmVVbmlmb3JtQXJpdHkgPSBhYnN0cmFjdChcbiAgJ2Fzc2VydENob2ljZXNIYXZlVW5pZm9ybUFyaXR5J1xuKTtcblxucGV4cHJzLmFueS5hc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eSA9XG4gIHBleHBycy5lbmQuYXNzZXJ0Q2hvaWNlc0hhdmVVbmlmb3JtQXJpdHkgPVxuICBwZXhwcnMuVGVybWluYWwucHJvdG90eXBlLmFzc2VydENob2ljZXNIYXZlVW5pZm9ybUFyaXR5ID1cbiAgcGV4cHJzLlJhbmdlLnByb3RvdHlwZS5hc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eSA9XG4gIHBleHBycy5QYXJhbS5wcm90b3R5cGUuYXNzZXJ0Q2hvaWNlc0hhdmVVbmlmb3JtQXJpdHkgPVxuICBwZXhwcnMuTGV4LnByb3RvdHlwZS5hc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eSA9XG4gIHBleHBycy5Vbmljb2RlQ2hhci5wcm90b3R5cGUuYXNzZXJ0Q2hvaWNlc0hhdmVVbmlmb3JtQXJpdHkgPVxuICAgIGZ1bmN0aW9uIChydWxlTmFtZSkge1xuICAgICAgLy8gbm8tb3BcbiAgICB9O1xuXG5wZXhwcnMuQWx0LnByb3RvdHlwZS5hc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eSA9IGZ1bmN0aW9uIChydWxlTmFtZSkge1xuICBpZiAodGhpcy50ZXJtcy5sZW5ndGggPT09IDApIHtcbiAgICByZXR1cm47XG4gIH1cbiAgY29uc3QgYXJpdHkgPSB0aGlzLnRlcm1zWzBdLmdldEFyaXR5KCk7XG4gIGZvciAobGV0IGlkeCA9IDA7IGlkeCA8IHRoaXMudGVybXMubGVuZ3RoOyBpZHgrKykge1xuICAgIGNvbnN0IHRlcm0gPSB0aGlzLnRlcm1zW2lkeF07XG4gICAgdGVybS5hc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eSgpO1xuICAgIGNvbnN0IG90aGVyQXJpdHkgPSB0ZXJtLmdldEFyaXR5KCk7XG4gICAgaWYgKGFyaXR5ICE9PSBvdGhlckFyaXR5KSB7XG4gICAgICB0aHJvdyBlcnJvcnMuaW5jb25zaXN0ZW50QXJpdHkocnVsZU5hbWUsIGFyaXR5LCBvdGhlckFyaXR5LCB0ZXJtKTtcbiAgICB9XG4gIH1cbn07XG5cbnBleHBycy5FeHRlbmQucHJvdG90eXBlLmFzc2VydENob2ljZXNIYXZlVW5pZm9ybUFyaXR5ID0gZnVuY3Rpb24gKHJ1bGVOYW1lKSB7XG4gIC8vIEV4dGVuZCBpcyBhIHNwZWNpYWwgY2FzZSBvZiBBbHQgdGhhdCdzIGd1YXJhbnRlZWQgdG8gaGF2ZSBleGFjdGx5IHR3b1xuICAvLyBjYXNlczogW2V4dGVuc2lvbnMsIG9yaWdCb2R5XS5cbiAgY29uc3QgYWN0dWFsQXJpdHkgPSB0aGlzLnRlcm1zWzBdLmdldEFyaXR5KCk7XG4gIGNvbnN0IGV4cGVjdGVkQXJpdHkgPSB0aGlzLnRlcm1zWzFdLmdldEFyaXR5KCk7XG4gIGlmIChhY3R1YWxBcml0eSAhPT0gZXhwZWN0ZWRBcml0eSkge1xuICAgIHRocm93IGVycm9ycy5pbmNvbnNpc3RlbnRBcml0eShydWxlTmFtZSwgZXhwZWN0ZWRBcml0eSwgYWN0dWFsQXJpdHksIHRoaXMudGVybXNbMF0pO1xuICB9XG59O1xuXG5wZXhwcnMuU2VxLnByb3RvdHlwZS5hc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eSA9IGZ1bmN0aW9uIChydWxlTmFtZSkge1xuICBmb3IgKGxldCBpZHggPSAwOyBpZHggPCB0aGlzLmZhY3RvcnMubGVuZ3RoOyBpZHgrKykge1xuICAgIHRoaXMuZmFjdG9yc1tpZHhdLmFzc2VydENob2ljZXNIYXZlVW5pZm9ybUFyaXR5KHJ1bGVOYW1lKTtcbiAgfVxufTtcblxucGV4cHJzLkl0ZXIucHJvdG90eXBlLmFzc2VydENob2ljZXNIYXZlVW5pZm9ybUFyaXR5ID0gZnVuY3Rpb24gKHJ1bGVOYW1lKSB7XG4gIHRoaXMuZXhwci5hc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eShydWxlTmFtZSk7XG59O1xuXG5wZXhwcnMuTm90LnByb3RvdHlwZS5hc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eSA9IGZ1bmN0aW9uIChydWxlTmFtZSkge1xuICAvLyBuby1vcCAobm90IHJlcXVpcmVkIGIvYyB0aGUgbmVzdGVkIGV4cHIgZG9lc24ndCBzaG93IHVwIGluIHRoZSBDU1QpXG59O1xuXG5wZXhwcnMuTG9va2FoZWFkLnByb3RvdHlwZS5hc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eSA9IGZ1bmN0aW9uIChydWxlTmFtZSkge1xuICB0aGlzLmV4cHIuYXNzZXJ0Q2hvaWNlc0hhdmVVbmlmb3JtQXJpdHkocnVsZU5hbWUpO1xufTtcblxucGV4cHJzLkFwcGx5LnByb3RvdHlwZS5hc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eSA9IGZ1bmN0aW9uIChydWxlTmFtZSkge1xuICAvLyBUaGUgYXJpdGllcyBvZiB0aGUgcGFyYW1ldGVyIGV4cHJlc3Npb25zIGlzIHJlcXVpcmVkIHRvIGJlIDEgYnlcbiAgLy8gYGFzc2VydEFsbEFwcGxpY2F0aW9uc0FyZVZhbGlkKClgLlxufTtcbiIsImltcG9ydCB7YWJzdHJhY3R9IGZyb20gJy4vY29tbW9uLmpzJztcbmltcG9ydCAqIGFzIGVycm9ycyBmcm9tICcuL2Vycm9ycy5qcyc7XG5pbXBvcnQgKiBhcyBwZXhwcnMgZnJvbSAnLi9wZXhwcnMtbWFpbi5qcyc7XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG4vLyBPcGVyYXRpb25zXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuXG5wZXhwcnMuUEV4cHIucHJvdG90eXBlLmFzc2VydEl0ZXJhdGVkRXhwcnNBcmVOb3ROdWxsYWJsZSA9IGFic3RyYWN0KFxuICAnYXNzZXJ0SXRlcmF0ZWRFeHByc0FyZU5vdE51bGxhYmxlJ1xuKTtcblxucGV4cHJzLmFueS5hc3NlcnRJdGVyYXRlZEV4cHJzQXJlTm90TnVsbGFibGUgPVxuICBwZXhwcnMuZW5kLmFzc2VydEl0ZXJhdGVkRXhwcnNBcmVOb3ROdWxsYWJsZSA9XG4gIHBleHBycy5UZXJtaW5hbC5wcm90b3R5cGUuYXNzZXJ0SXRlcmF0ZWRFeHByc0FyZU5vdE51bGxhYmxlID1cbiAgcGV4cHJzLlJhbmdlLnByb3RvdHlwZS5hc3NlcnRJdGVyYXRlZEV4cHJzQXJlTm90TnVsbGFibGUgPVxuICBwZXhwcnMuUGFyYW0ucHJvdG90eXBlLmFzc2VydEl0ZXJhdGVkRXhwcnNBcmVOb3ROdWxsYWJsZSA9XG4gIHBleHBycy5Vbmljb2RlQ2hhci5wcm90b3R5cGUuYXNzZXJ0SXRlcmF0ZWRFeHByc0FyZU5vdE51bGxhYmxlID1cbiAgICBmdW5jdGlvbiAoZ3JhbW1hcikge1xuICAgICAgLy8gbm8tb3BcbiAgICB9O1xuXG5wZXhwcnMuQWx0LnByb3RvdHlwZS5hc3NlcnRJdGVyYXRlZEV4cHJzQXJlTm90TnVsbGFibGUgPSBmdW5jdGlvbiAoZ3JhbW1hcikge1xuICBmb3IgKGxldCBpZHggPSAwOyBpZHggPCB0aGlzLnRlcm1zLmxlbmd0aDsgaWR4KyspIHtcbiAgICB0aGlzLnRlcm1zW2lkeF0uYXNzZXJ0SXRlcmF0ZWRFeHByc0FyZU5vdE51bGxhYmxlKGdyYW1tYXIpO1xuICB9XG59O1xuXG5wZXhwcnMuU2VxLnByb3RvdHlwZS5hc3NlcnRJdGVyYXRlZEV4cHJzQXJlTm90TnVsbGFibGUgPSBmdW5jdGlvbiAoZ3JhbW1hcikge1xuICBmb3IgKGxldCBpZHggPSAwOyBpZHggPCB0aGlzLmZhY3RvcnMubGVuZ3RoOyBpZHgrKykge1xuICAgIHRoaXMuZmFjdG9yc1tpZHhdLmFzc2VydEl0ZXJhdGVkRXhwcnNBcmVOb3ROdWxsYWJsZShncmFtbWFyKTtcbiAgfVxufTtcblxucGV4cHJzLkl0ZXIucHJvdG90eXBlLmFzc2VydEl0ZXJhdGVkRXhwcnNBcmVOb3ROdWxsYWJsZSA9IGZ1bmN0aW9uIChncmFtbWFyKSB7XG4gIC8vIE5vdGU6IHRoaXMgaXMgdGhlIGltcGxlbWVudGF0aW9uIG9mIHRoaXMgbWV0aG9kIGZvciBgU3RhcmAgYW5kIGBQbHVzYCBleHByZXNzaW9ucy5cbiAgLy8gSXQgaXMgb3ZlcnJpZGRlbiBmb3IgYE9wdGAgYmVsb3cuXG4gIHRoaXMuZXhwci5hc3NlcnRJdGVyYXRlZEV4cHJzQXJlTm90TnVsbGFibGUoZ3JhbW1hcik7XG4gIGlmICh0aGlzLmV4cHIuaXNOdWxsYWJsZShncmFtbWFyKSkge1xuICAgIHRocm93IGVycm9ycy5rbGVlbmVFeHBySGFzTnVsbGFibGVPcGVyYW5kKHRoaXMsIFtdKTtcbiAgfVxufTtcblxucGV4cHJzLk9wdC5wcm90b3R5cGUuYXNzZXJ0SXRlcmF0ZWRFeHByc0FyZU5vdE51bGxhYmxlID1cbiAgcGV4cHJzLk5vdC5wcm90b3R5cGUuYXNzZXJ0SXRlcmF0ZWRFeHByc0FyZU5vdE51bGxhYmxlID1cbiAgcGV4cHJzLkxvb2thaGVhZC5wcm90b3R5cGUuYXNzZXJ0SXRlcmF0ZWRFeHByc0FyZU5vdE51bGxhYmxlID1cbiAgcGV4cHJzLkxleC5wcm90b3R5cGUuYXNzZXJ0SXRlcmF0ZWRFeHByc0FyZU5vdE51bGxhYmxlID1cbiAgICBmdW5jdGlvbiAoZ3JhbW1hcikge1xuICAgICAgdGhpcy5leHByLmFzc2VydEl0ZXJhdGVkRXhwcnNBcmVOb3ROdWxsYWJsZShncmFtbWFyKTtcbiAgICB9O1xuXG5wZXhwcnMuQXBwbHkucHJvdG90eXBlLmFzc2VydEl0ZXJhdGVkRXhwcnNBcmVOb3ROdWxsYWJsZSA9IGZ1bmN0aW9uIChncmFtbWFyKSB7XG4gIHRoaXMuYXJncy5mb3JFYWNoKGFyZyA9PiB7XG4gICAgYXJnLmFzc2VydEl0ZXJhdGVkRXhwcnNBcmVOb3ROdWxsYWJsZShncmFtbWFyKTtcbiAgfSk7XG59O1xuIiwiaW1wb3J0ICogYXMgY29tbW9uIGZyb20gJy4vY29tbW9uLmpzJztcblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cbi8vIFByaXZhdGUgc3R1ZmZcbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG5cbmV4cG9ydCBjbGFzcyBOb2RlIHtcbiAgY29uc3RydWN0b3IobWF0Y2hMZW5ndGgpIHtcbiAgICB0aGlzLm1hdGNoTGVuZ3RoID0gbWF0Y2hMZW5ndGg7XG4gIH1cblxuICBnZXQgY3Rvck5hbWUoKSB7XG4gICAgdGhyb3cgbmV3IEVycm9yKCdzdWJjbGFzcyByZXNwb25zaWJpbGl0eScpO1xuICB9XG5cbiAgbnVtQ2hpbGRyZW4oKSB7XG4gICAgcmV0dXJuIHRoaXMuY2hpbGRyZW4gPyB0aGlzLmNoaWxkcmVuLmxlbmd0aCA6IDA7XG4gIH1cblxuICBjaGlsZEF0KGlkeCkge1xuICAgIGlmICh0aGlzLmNoaWxkcmVuKSB7XG4gICAgICByZXR1cm4gdGhpcy5jaGlsZHJlbltpZHhdO1xuICAgIH1cbiAgfVxuXG4gIGluZGV4T2ZDaGlsZChhcmcpIHtcbiAgICByZXR1cm4gdGhpcy5jaGlsZHJlbi5pbmRleE9mKGFyZyk7XG4gIH1cblxuICBoYXNDaGlsZHJlbigpIHtcbiAgICByZXR1cm4gdGhpcy5udW1DaGlsZHJlbigpID4gMDtcbiAgfVxuXG4gIGhhc05vQ2hpbGRyZW4oKSB7XG4gICAgcmV0dXJuICF0aGlzLmhhc0NoaWxkcmVuKCk7XG4gIH1cblxuICBvbmx5Q2hpbGQoKSB7XG4gICAgaWYgKHRoaXMubnVtQ2hpbGRyZW4oKSAhPT0gMSkge1xuICAgICAgdGhyb3cgbmV3IEVycm9yKFxuICAgICAgICAnY2Fubm90IGdldCBvbmx5IGNoaWxkIG9mIGEgbm9kZSBvZiB0eXBlICcgK1xuICAgICAgICAgIHRoaXMuY3Rvck5hbWUgK1xuICAgICAgICAgICcgKGl0IGhhcyAnICtcbiAgICAgICAgICB0aGlzLm51bUNoaWxkcmVuKCkgK1xuICAgICAgICAgICcgY2hpbGRyZW4pJ1xuICAgICAgKTtcbiAgICB9IGVsc2Uge1xuICAgICAgcmV0dXJuIHRoaXMuZmlyc3RDaGlsZCgpO1xuICAgIH1cbiAgfVxuXG4gIGZpcnN0Q2hpbGQoKSB7XG4gICAgaWYgKHRoaXMuaGFzTm9DaGlsZHJlbigpKSB7XG4gICAgICB0aHJvdyBuZXcgRXJyb3IoXG4gICAgICAgICdjYW5ub3QgZ2V0IGZpcnN0IGNoaWxkIG9mIGEgJyArIHRoaXMuY3Rvck5hbWUgKyAnIG5vZGUsIHdoaWNoIGhhcyBubyBjaGlsZHJlbidcbiAgICAgICk7XG4gICAgfSBlbHNlIHtcbiAgICAgIHJldHVybiB0aGlzLmNoaWxkQXQoMCk7XG4gICAgfVxuICB9XG5cbiAgbGFzdENoaWxkKCkge1xuICAgIGlmICh0aGlzLmhhc05vQ2hpbGRyZW4oKSkge1xuICAgICAgdGhyb3cgbmV3IEVycm9yKFxuICAgICAgICAnY2Fubm90IGdldCBsYXN0IGNoaWxkIG9mIGEgJyArIHRoaXMuY3Rvck5hbWUgKyAnIG5vZGUsIHdoaWNoIGhhcyBubyBjaGlsZHJlbidcbiAgICAgICk7XG4gICAgfSBlbHNlIHtcbiAgICAgIHJldHVybiB0aGlzLmNoaWxkQXQodGhpcy5udW1DaGlsZHJlbigpIC0gMSk7XG4gICAgfVxuICB9XG5cbiAgY2hpbGRCZWZvcmUoY2hpbGQpIHtcbiAgICBjb25zdCBjaGlsZElkeCA9IHRoaXMuaW5kZXhPZkNoaWxkKGNoaWxkKTtcbiAgICBpZiAoY2hpbGRJZHggPCAwKSB7XG4gICAgICB0aHJvdyBuZXcgRXJyb3IoJ05vZGUuY2hpbGRCZWZvcmUoKSBjYWxsZWQgdy8gYW4gYXJndW1lbnQgdGhhdCBpcyBub3QgYSBjaGlsZCcpO1xuICAgIH0gZWxzZSBpZiAoY2hpbGRJZHggPT09IDApIHtcbiAgICAgIHRocm93IG5ldyBFcnJvcignY2Fubm90IGdldCBjaGlsZCBiZWZvcmUgZmlyc3QgY2hpbGQnKTtcbiAgICB9IGVsc2Uge1xuICAgICAgcmV0dXJuIHRoaXMuY2hpbGRBdChjaGlsZElkeCAtIDEpO1xuICAgIH1cbiAgfVxuXG4gIGNoaWxkQWZ0ZXIoY2hpbGQpIHtcbiAgICBjb25zdCBjaGlsZElkeCA9IHRoaXMuaW5kZXhPZkNoaWxkKGNoaWxkKTtcbiAgICBpZiAoY2hpbGRJZHggPCAwKSB7XG4gICAgICB0aHJvdyBuZXcgRXJyb3IoJ05vZGUuY2hpbGRBZnRlcigpIGNhbGxlZCB3LyBhbiBhcmd1bWVudCB0aGF0IGlzIG5vdCBhIGNoaWxkJyk7XG4gICAgfSBlbHNlIGlmIChjaGlsZElkeCA9PT0gdGhpcy5udW1DaGlsZHJlbigpIC0gMSkge1xuICAgICAgdGhyb3cgbmV3IEVycm9yKCdjYW5ub3QgZ2V0IGNoaWxkIGFmdGVyIGxhc3QgY2hpbGQnKTtcbiAgICB9IGVsc2Uge1xuICAgICAgcmV0dXJuIHRoaXMuY2hpbGRBdChjaGlsZElkeCArIDEpO1xuICAgIH1cbiAgfVxuXG4gIGlzVGVybWluYWwoKSB7XG4gICAgcmV0dXJuIGZhbHNlO1xuICB9XG5cbiAgaXNOb250ZXJtaW5hbCgpIHtcbiAgICByZXR1cm4gZmFsc2U7XG4gIH1cblxuICBpc0l0ZXJhdGlvbigpIHtcbiAgICByZXR1cm4gZmFsc2U7XG4gIH1cblxuICBpc09wdGlvbmFsKCkge1xuICAgIHJldHVybiBmYWxzZTtcbiAgfVxufVxuXG4vLyBUZXJtaW5hbHNcblxuZXhwb3J0IGNsYXNzIFRlcm1pbmFsTm9kZSBleHRlbmRzIE5vZGUge1xuICBnZXQgY3Rvck5hbWUoKSB7XG4gICAgcmV0dXJuICdfdGVybWluYWwnO1xuICB9XG5cbiAgaXNUZXJtaW5hbCgpIHtcbiAgICByZXR1cm4gdHJ1ZTtcbiAgfVxuXG4gIGdldCBwcmltaXRpdmVWYWx1ZSgpIHtcbiAgICB0aHJvdyBuZXcgRXJyb3IoJ1RoZSBgcHJpbWl0aXZlVmFsdWVgIHByb3BlcnR5IHdhcyByZW1vdmVkIGluIE9obSB2MTcuJyk7XG4gIH1cbn1cblxuLy8gTm9udGVybWluYWxzXG5cbmV4cG9ydCBjbGFzcyBOb250ZXJtaW5hbE5vZGUgZXh0ZW5kcyBOb2RlIHtcbiAgY29uc3RydWN0b3IocnVsZU5hbWUsIGNoaWxkcmVuLCBjaGlsZE9mZnNldHMsIG1hdGNoTGVuZ3RoKSB7XG4gICAgc3VwZXIobWF0Y2hMZW5ndGgpO1xuICAgIHRoaXMucnVsZU5hbWUgPSBydWxlTmFtZTtcbiAgICB0aGlzLmNoaWxkcmVuID0gY2hpbGRyZW47XG4gICAgdGhpcy5jaGlsZE9mZnNldHMgPSBjaGlsZE9mZnNldHM7XG4gIH1cblxuICBnZXQgY3Rvck5hbWUoKSB7XG4gICAgcmV0dXJuIHRoaXMucnVsZU5hbWU7XG4gIH1cblxuICBpc05vbnRlcm1pbmFsKCkge1xuICAgIHJldHVybiB0cnVlO1xuICB9XG5cbiAgaXNMZXhpY2FsKCkge1xuICAgIHJldHVybiBjb21tb24uaXNMZXhpY2FsKHRoaXMuY3Rvck5hbWUpO1xuICB9XG5cbiAgaXNTeW50YWN0aWMoKSB7XG4gICAgcmV0dXJuIGNvbW1vbi5pc1N5bnRhY3RpYyh0aGlzLmN0b3JOYW1lKTtcbiAgfVxufVxuXG4vLyBJdGVyYXRpb25zXG5cbmV4cG9ydCBjbGFzcyBJdGVyYXRpb25Ob2RlIGV4dGVuZHMgTm9kZSB7XG4gIGNvbnN0cnVjdG9yKGNoaWxkcmVuLCBjaGlsZE9mZnNldHMsIG1hdGNoTGVuZ3RoLCBpc09wdGlvbmFsKSB7XG4gICAgc3VwZXIobWF0Y2hMZW5ndGgpO1xuICAgIHRoaXMuY2hpbGRyZW4gPSBjaGlsZHJlbjtcbiAgICB0aGlzLmNoaWxkT2Zmc2V0cyA9IGNoaWxkT2Zmc2V0cztcbiAgICB0aGlzLm9wdGlvbmFsID0gaXNPcHRpb25hbDtcbiAgfVxuXG4gIGdldCBjdG9yTmFtZSgpIHtcbiAgICByZXR1cm4gJ19pdGVyJztcbiAgfVxuXG4gIGlzSXRlcmF0aW9uKCkge1xuICAgIHJldHVybiB0cnVlO1xuICB9XG5cbiAgaXNPcHRpb25hbCgpIHtcbiAgICByZXR1cm4gdGhpcy5vcHRpb25hbDtcbiAgfVxufVxuIiwiaW1wb3J0IHtUcmFjZX0gZnJvbSAnLi9UcmFjZS5qcyc7XG5pbXBvcnQgKiBhcyBjb21tb24gZnJvbSAnLi9jb21tb24uanMnO1xuaW1wb3J0ICogYXMgZXJyb3JzIGZyb20gJy4vZXJyb3JzLmpzJztcbmltcG9ydCB7SXRlcmF0aW9uTm9kZSwgTm9udGVybWluYWxOb2RlLCBUZXJtaW5hbE5vZGV9IGZyb20gJy4vbm9kZXMuanMnO1xuaW1wb3J0ICogYXMgcGV4cHJzIGZyb20gJy4vcGV4cHJzLW1haW4uanMnO1xuaW1wb3J0IHtNQVhfQ09ERV9QT0lOVH0gZnJvbSAnLi9JbnB1dFN0cmVhbS5qcyc7XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG4vLyBPcGVyYXRpb25zXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuXG4vKlxuICBFdmFsdWF0ZSB0aGUgZXhwcmVzc2lvbiBhbmQgcmV0dXJuIGB0cnVlYCBpZiBpdCBzdWNjZWVkcywgYGZhbHNlYCBvdGhlcndpc2UuIFRoaXMgbWV0aG9kIHNob3VsZFxuICBvbmx5IGJlIGNhbGxlZCBkaXJlY3RseSBieSBgU3RhdGUucHJvdG90eXBlLmV2YWwoZXhwcilgLCB3aGljaCBhbHNvIHVwZGF0ZXMgdGhlIGRhdGEgc3RydWN0dXJlc1xuICB0aGF0IGFyZSB1c2VkIGZvciB0cmFjaW5nLiAoTWFraW5nIHRob3NlIHVwZGF0ZXMgaW4gYSBtZXRob2Qgb2YgYFN0YXRlYCBlbmFibGVzIHRoZSB0cmFjZS1zcGVjaWZpY1xuICBkYXRhIHN0cnVjdHVyZXMgdG8gYmUgXCJzZWNyZXRzXCIgb2YgdGhhdCBjbGFzcywgd2hpY2ggaXMgZ29vZCBmb3IgbW9kdWxhcml0eS4pXG5cbiAgVGhlIGNvbnRyYWN0IG9mIHRoaXMgbWV0aG9kIGlzIGFzIGZvbGxvd3M6XG4gICogV2hlbiB0aGUgcmV0dXJuIHZhbHVlIGlzIGB0cnVlYCxcbiAgICAtIHRoZSBzdGF0ZSBvYmplY3Qgd2lsbCBoYXZlIGBleHByLmdldEFyaXR5KClgIG1vcmUgYmluZGluZ3MgdGhhbiBpdCBkaWQgYmVmb3JlIHRoZSBjYWxsLlxuICAqIFdoZW4gdGhlIHJldHVybiB2YWx1ZSBpcyBgZmFsc2VgLFxuICAgIC0gdGhlIHN0YXRlIG9iamVjdCBtYXkgaGF2ZSBtb3JlIGJpbmRpbmdzIHRoYW4gaXQgZGlkIGJlZm9yZSB0aGUgY2FsbCwgYW5kXG4gICAgLSBpdHMgaW5wdXQgc3RyZWFtJ3MgcG9zaXRpb24gbWF5IGJlIGFueXdoZXJlLlxuXG4gIE5vdGUgdGhhdCBgU3RhdGUucHJvdG90eXBlLmV2YWwoZXhwcilgLCB1bmxpa2UgdGhpcyBtZXRob2QsIGd1YXJhbnRlZXMgdGhhdCBuZWl0aGVyIHRoZSBzdGF0ZVxuICBvYmplY3QncyBiaW5kaW5ncyBub3IgaXRzIGlucHV0IHN0cmVhbSdzIHBvc2l0aW9uIHdpbGwgY2hhbmdlIGlmIHRoZSBleHByZXNzaW9uIGZhaWxzIHRvIG1hdGNoLlxuKi9cbnBleHBycy5QRXhwci5wcm90b3R5cGUuZXZhbCA9IGNvbW1vbi5hYnN0cmFjdCgnZXZhbCcpOyAvLyBmdW5jdGlvbihzdGF0ZSkgeyAuLi4gfVxuXG5wZXhwcnMuYW55LmV2YWwgPSBmdW5jdGlvbiAoc3RhdGUpIHtcbiAgY29uc3Qge2lucHV0U3RyZWFtfSA9IHN0YXRlO1xuICBjb25zdCBvcmlnUG9zID0gaW5wdXRTdHJlYW0ucG9zO1xuICBjb25zdCBjcCA9IGlucHV0U3RyZWFtLm5leHRDb2RlUG9pbnQoKTtcbiAgaWYgKGNwICE9PSB1bmRlZmluZWQpIHtcbiAgICBzdGF0ZS5wdXNoQmluZGluZyhuZXcgVGVybWluYWxOb2RlKFN0cmluZy5mcm9tQ29kZVBvaW50KGNwKS5sZW5ndGgpLCBvcmlnUG9zKTtcbiAgICByZXR1cm4gdHJ1ZTtcbiAgfSBlbHNlIHtcbiAgICBzdGF0ZS5wcm9jZXNzRmFpbHVyZShvcmlnUG9zLCB0aGlzKTtcbiAgICByZXR1cm4gZmFsc2U7XG4gIH1cbn07XG5cbnBleHBycy5lbmQuZXZhbCA9IGZ1bmN0aW9uIChzdGF0ZSkge1xuICBjb25zdCB7aW5wdXRTdHJlYW19ID0gc3RhdGU7XG4gIGNvbnN0IG9yaWdQb3MgPSBpbnB1dFN0cmVhbS5wb3M7XG4gIGlmIChpbnB1dFN0cmVhbS5hdEVuZCgpKSB7XG4gICAgc3RhdGUucHVzaEJpbmRpbmcobmV3IFRlcm1pbmFsTm9kZSgwKSwgb3JpZ1Bvcyk7XG4gICAgcmV0dXJuIHRydWU7XG4gIH0gZWxzZSB7XG4gICAgc3RhdGUucHJvY2Vzc0ZhaWx1cmUob3JpZ1BvcywgdGhpcyk7XG4gICAgcmV0dXJuIGZhbHNlO1xuICB9XG59O1xuXG5wZXhwcnMuVGVybWluYWwucHJvdG90eXBlLmV2YWwgPSBmdW5jdGlvbiAoc3RhdGUpIHtcbiAgY29uc3Qge2lucHV0U3RyZWFtfSA9IHN0YXRlO1xuICBjb25zdCBvcmlnUG9zID0gaW5wdXRTdHJlYW0ucG9zO1xuICBpZiAoIWlucHV0U3RyZWFtLm1hdGNoU3RyaW5nKHRoaXMub2JqKSkge1xuICAgIHN0YXRlLnByb2Nlc3NGYWlsdXJlKG9yaWdQb3MsIHRoaXMpO1xuICAgIHJldHVybiBmYWxzZTtcbiAgfSBlbHNlIHtcbiAgICBzdGF0ZS5wdXNoQmluZGluZyhuZXcgVGVybWluYWxOb2RlKHRoaXMub2JqLmxlbmd0aCksIG9yaWdQb3MpO1xuICAgIHJldHVybiB0cnVlO1xuICB9XG59O1xuXG5wZXhwcnMuUmFuZ2UucHJvdG90eXBlLmV2YWwgPSBmdW5jdGlvbiAoc3RhdGUpIHtcbiAgY29uc3Qge2lucHV0U3RyZWFtfSA9IHN0YXRlO1xuICBjb25zdCBvcmlnUG9zID0gaW5wdXRTdHJlYW0ucG9zO1xuXG4gIC8vIEEgcmFuZ2UgY2FuIG9wZXJhdGUgaW4gb25lIG9mIHR3byBtb2RlczogbWF0Y2hpbmcgYSBzaW5nbGUsIDE2LWJpdCBfY29kZSB1bml0XyxcbiAgLy8gb3IgbWF0Y2hpbmcgYSBfY29kZSBwb2ludF8uIChDb2RlIHBvaW50cyBvdmVyIDB4RkZGRiB0YWtlIHVwIHR3byAxNi1iaXQgY29kZSB1bml0cy4pXG4gIGNvbnN0IGNwID0gdGhpcy5tYXRjaENvZGVQb2ludCA/IGlucHV0U3RyZWFtLm5leHRDb2RlUG9pbnQoKSA6IGlucHV0U3RyZWFtLm5leHRDaGFyQ29kZSgpO1xuXG4gIC8vIEFsd2F5cyBjb21wYXJlIGJ5IGNvZGUgcG9pbnQgdmFsdWUgdG8gZ2V0IHRoZSBjb3JyZWN0IHJlc3VsdCBpbiBhbGwgc2NlbmFyaW9zLlxuICAvLyBOb3RlIHRoYXQgZm9yIHN0cmluZ3Mgb2YgbGVuZ3RoIDEsIGNvZGVQb2ludEF0KDApIGFuZCBjaGFyUG9pbnRBdCgwKSBhcmUgZXF1aXZhbGVudC5cbiAgaWYgKGNwICE9PSB1bmRlZmluZWQgJiYgdGhpcy5mcm9tLmNvZGVQb2ludEF0KDApIDw9IGNwICYmIGNwIDw9IHRoaXMudG8uY29kZVBvaW50QXQoMCkpIHtcbiAgICBzdGF0ZS5wdXNoQmluZGluZyhuZXcgVGVybWluYWxOb2RlKFN0cmluZy5mcm9tQ29kZVBvaW50KGNwKS5sZW5ndGgpLCBvcmlnUG9zKTtcbiAgICByZXR1cm4gdHJ1ZTtcbiAgfSBlbHNlIHtcbiAgICBzdGF0ZS5wcm9jZXNzRmFpbHVyZShvcmlnUG9zLCB0aGlzKTtcbiAgICByZXR1cm4gZmFsc2U7XG4gIH1cbn07XG5cbnBleHBycy5QYXJhbS5wcm90b3R5cGUuZXZhbCA9IGZ1bmN0aW9uIChzdGF0ZSkge1xuICByZXR1cm4gc3RhdGUuZXZhbChzdGF0ZS5jdXJyZW50QXBwbGljYXRpb24oKS5hcmdzW3RoaXMuaW5kZXhdKTtcbn07XG5cbnBleHBycy5MZXgucHJvdG90eXBlLmV2YWwgPSBmdW5jdGlvbiAoc3RhdGUpIHtcbiAgc3RhdGUuZW50ZXJMZXhpZmllZENvbnRleHQoKTtcbiAgY29uc3QgYW5zID0gc3RhdGUuZXZhbCh0aGlzLmV4cHIpO1xuICBzdGF0ZS5leGl0TGV4aWZpZWRDb250ZXh0KCk7XG4gIHJldHVybiBhbnM7XG59O1xuXG5wZXhwcnMuQWx0LnByb3RvdHlwZS5ldmFsID0gZnVuY3Rpb24gKHN0YXRlKSB7XG4gIGZvciAobGV0IGlkeCA9IDA7IGlkeCA8IHRoaXMudGVybXMubGVuZ3RoOyBpZHgrKykge1xuICAgIGlmIChzdGF0ZS5ldmFsKHRoaXMudGVybXNbaWR4XSkpIHtcbiAgICAgIHJldHVybiB0cnVlO1xuICAgIH1cbiAgfVxuICByZXR1cm4gZmFsc2U7XG59O1xuXG5wZXhwcnMuU2VxLnByb3RvdHlwZS5ldmFsID0gZnVuY3Rpb24gKHN0YXRlKSB7XG4gIGZvciAobGV0IGlkeCA9IDA7IGlkeCA8IHRoaXMuZmFjdG9ycy5sZW5ndGg7IGlkeCsrKSB7XG4gICAgY29uc3QgZmFjdG9yID0gdGhpcy5mYWN0b3JzW2lkeF07XG4gICAgaWYgKCFzdGF0ZS5ldmFsKGZhY3RvcikpIHtcbiAgICAgIHJldHVybiBmYWxzZTtcbiAgICB9XG4gIH1cbiAgcmV0dXJuIHRydWU7XG59O1xuXG5wZXhwcnMuSXRlci5wcm90b3R5cGUuZXZhbCA9IGZ1bmN0aW9uIChzdGF0ZSkge1xuICBjb25zdCB7aW5wdXRTdHJlYW19ID0gc3RhdGU7XG4gIGNvbnN0IG9yaWdQb3MgPSBpbnB1dFN0cmVhbS5wb3M7XG4gIGNvbnN0IGFyaXR5ID0gdGhpcy5nZXRBcml0eSgpO1xuICBjb25zdCBjb2xzID0gW107XG4gIGNvbnN0IGNvbE9mZnNldHMgPSBbXTtcbiAgd2hpbGUgKGNvbHMubGVuZ3RoIDwgYXJpdHkpIHtcbiAgICBjb2xzLnB1c2goW10pO1xuICAgIGNvbE9mZnNldHMucHVzaChbXSk7XG4gIH1cblxuICBsZXQgbnVtTWF0Y2hlcyA9IDA7XG4gIGxldCBwcmV2UG9zID0gb3JpZ1BvcztcbiAgbGV0IGlkeDtcbiAgd2hpbGUgKG51bU1hdGNoZXMgPCB0aGlzLm1heE51bU1hdGNoZXMgJiYgc3RhdGUuZXZhbCh0aGlzLmV4cHIpKSB7XG4gICAgaWYgKGlucHV0U3RyZWFtLnBvcyA9PT0gcHJldlBvcykge1xuICAgICAgdGhyb3cgZXJyb3JzLmtsZWVuZUV4cHJIYXNOdWxsYWJsZU9wZXJhbmQodGhpcywgc3RhdGUuX2FwcGxpY2F0aW9uU3RhY2spO1xuICAgIH1cbiAgICBwcmV2UG9zID0gaW5wdXRTdHJlYW0ucG9zO1xuICAgIG51bU1hdGNoZXMrKztcbiAgICBjb25zdCByb3cgPSBzdGF0ZS5fYmluZGluZ3Muc3BsaWNlKHN0YXRlLl9iaW5kaW5ncy5sZW5ndGggLSBhcml0eSwgYXJpdHkpO1xuICAgIGNvbnN0IHJvd09mZnNldHMgPSBzdGF0ZS5fYmluZGluZ09mZnNldHMuc3BsaWNlKFxuICAgICAgc3RhdGUuX2JpbmRpbmdPZmZzZXRzLmxlbmd0aCAtIGFyaXR5LFxuICAgICAgYXJpdHlcbiAgICApO1xuICAgIGZvciAoaWR4ID0gMDsgaWR4IDwgcm93Lmxlbmd0aDsgaWR4KyspIHtcbiAgICAgIGNvbHNbaWR4XS5wdXNoKHJvd1tpZHhdKTtcbiAgICAgIGNvbE9mZnNldHNbaWR4XS5wdXNoKHJvd09mZnNldHNbaWR4XSk7XG4gICAgfVxuICB9XG4gIGlmIChudW1NYXRjaGVzIDwgdGhpcy5taW5OdW1NYXRjaGVzKSB7XG4gICAgcmV0dXJuIGZhbHNlO1xuICB9XG4gIGxldCBvZmZzZXQgPSBzdGF0ZS5wb3NUb09mZnNldChvcmlnUG9zKTtcbiAgbGV0IG1hdGNoTGVuZ3RoID0gMDtcbiAgaWYgKG51bU1hdGNoZXMgPiAwKSB7XG4gICAgY29uc3QgbGFzdENvbCA9IGNvbHNbYXJpdHkgLSAxXTtcbiAgICBjb25zdCBsYXN0Q29sT2Zmc2V0cyA9IGNvbE9mZnNldHNbYXJpdHkgLSAxXTtcblxuICAgIGNvbnN0IGVuZE9mZnNldCA9XG4gICAgICBsYXN0Q29sT2Zmc2V0c1tsYXN0Q29sT2Zmc2V0cy5sZW5ndGggLSAxXSArIGxhc3RDb2xbbGFzdENvbC5sZW5ndGggLSAxXS5tYXRjaExlbmd0aDtcbiAgICBvZmZzZXQgPSBjb2xPZmZzZXRzWzBdWzBdO1xuICAgIG1hdGNoTGVuZ3RoID0gZW5kT2Zmc2V0IC0gb2Zmc2V0O1xuICB9XG4gIGNvbnN0IGlzT3B0aW9uYWwgPSB0aGlzIGluc3RhbmNlb2YgcGV4cHJzLk9wdDtcbiAgZm9yIChpZHggPSAwOyBpZHggPCBjb2xzLmxlbmd0aDsgaWR4KyspIHtcbiAgICBzdGF0ZS5fYmluZGluZ3MucHVzaChcbiAgICAgIG5ldyBJdGVyYXRpb25Ob2RlKGNvbHNbaWR4XSwgY29sT2Zmc2V0c1tpZHhdLCBtYXRjaExlbmd0aCwgaXNPcHRpb25hbClcbiAgICApO1xuICAgIHN0YXRlLl9iaW5kaW5nT2Zmc2V0cy5wdXNoKG9mZnNldCk7XG4gIH1cbiAgcmV0dXJuIHRydWU7XG59O1xuXG5wZXhwcnMuTm90LnByb3RvdHlwZS5ldmFsID0gZnVuY3Rpb24gKHN0YXRlKSB7XG4gIC8qXG4gICAgVE9ETzpcbiAgICAtIFJpZ2h0IG5vdyB3ZSdyZSBqdXN0IHRocm93aW5nIGF3YXkgYWxsIG9mIHRoZSBmYWlsdXJlcyB0aGF0IGhhcHBlbiBpbnNpZGUgYSBgbm90YCwgYW5kXG4gICAgICByZWNvcmRpbmcgYHRoaXNgIGFzIGEgZmFpbGVkIGV4cHJlc3Npb24uXG4gICAgLSBEb3VibGUgbmVnYXRpb24gc2hvdWxkIGJlIGVxdWl2YWxlbnQgdG8gbG9va2FoZWFkLCBidXQgdGhhdCdzIG5vdCB0aGUgY2FzZSByaWdodCBub3cgd3J0XG4gICAgICBmYWlsdXJlcy4gRS5nLiwgfn4nZm9vJyBwcm9kdWNlcyBhIGZhaWx1cmUgZm9yIH5+J2ZvbycsIGJ1dCBtYXliZSBpdCBzaG91bGQgcHJvZHVjZVxuICAgICAgYSBmYWlsdXJlIGZvciAnZm9vJyBpbnN0ZWFkLlxuICAqL1xuXG4gIGNvbnN0IHtpbnB1dFN0cmVhbX0gPSBzdGF0ZTtcbiAgY29uc3Qgb3JpZ1BvcyA9IGlucHV0U3RyZWFtLnBvcztcbiAgc3RhdGUucHVzaEZhaWx1cmVzSW5mbygpO1xuXG4gIGNvbnN0IGFucyA9IHN0YXRlLmV2YWwodGhpcy5leHByKTtcblxuICBzdGF0ZS5wb3BGYWlsdXJlc0luZm8oKTtcbiAgaWYgKGFucykge1xuICAgIHN0YXRlLnByb2Nlc3NGYWlsdXJlKG9yaWdQb3MsIHRoaXMpO1xuICAgIHJldHVybiBmYWxzZTtcbiAgfVxuXG4gIGlucHV0U3RyZWFtLnBvcyA9IG9yaWdQb3M7XG4gIHJldHVybiB0cnVlO1xufTtcblxucGV4cHJzLkxvb2thaGVhZC5wcm90b3R5cGUuZXZhbCA9IGZ1bmN0aW9uIChzdGF0ZSkge1xuICBjb25zdCB7aW5wdXRTdHJlYW19ID0gc3RhdGU7XG4gIGNvbnN0IG9yaWdQb3MgPSBpbnB1dFN0cmVhbS5wb3M7XG4gIGlmIChzdGF0ZS5ldmFsKHRoaXMuZXhwcikpIHtcbiAgICBpbnB1dFN0cmVhbS5wb3MgPSBvcmlnUG9zO1xuICAgIHJldHVybiB0cnVlO1xuICB9IGVsc2Uge1xuICAgIHJldHVybiBmYWxzZTtcbiAgfVxufTtcblxucGV4cHJzLkFwcGx5LnByb3RvdHlwZS5ldmFsID0gZnVuY3Rpb24gKHN0YXRlKSB7XG4gIGNvbnN0IGNhbGxlciA9IHN0YXRlLmN1cnJlbnRBcHBsaWNhdGlvbigpO1xuICBjb25zdCBhY3R1YWxzID0gY2FsbGVyID8gY2FsbGVyLmFyZ3MgOiBbXTtcbiAgY29uc3QgYXBwID0gdGhpcy5zdWJzdGl0dXRlUGFyYW1zKGFjdHVhbHMpO1xuXG4gIGNvbnN0IHBvc0luZm8gPSBzdGF0ZS5nZXRDdXJyZW50UG9zSW5mbygpO1xuICBpZiAocG9zSW5mby5pc0FjdGl2ZShhcHApKSB7XG4gICAgLy8gVGhpcyBydWxlIGlzIGFscmVhZHkgYWN0aXZlIGF0IHRoaXMgcG9zaXRpb24sIGkuZS4sIGl0IGlzIGxlZnQtcmVjdXJzaXZlLlxuICAgIHJldHVybiBhcHAuaGFuZGxlQ3ljbGUoc3RhdGUpO1xuICB9XG5cbiAgY29uc3QgbWVtb0tleSA9IGFwcC50b01lbW9LZXkoKTtcbiAgY29uc3QgbWVtb1JlYyA9IHBvc0luZm8ubWVtb1ttZW1vS2V5XTtcblxuICBpZiAobWVtb1JlYyAmJiBwb3NJbmZvLnNob3VsZFVzZU1lbW9pemVkUmVzdWx0KG1lbW9SZWMpKSB7XG4gICAgaWYgKHN0YXRlLmhhc05lY2Vzc2FyeUluZm8obWVtb1JlYykpIHtcbiAgICAgIHJldHVybiBzdGF0ZS51c2VNZW1vaXplZFJlc3VsdChzdGF0ZS5pbnB1dFN0cmVhbS5wb3MsIG1lbW9SZWMpO1xuICAgIH1cbiAgICBkZWxldGUgcG9zSW5mby5tZW1vW21lbW9LZXldO1xuICB9XG4gIHJldHVybiBhcHAucmVhbGx5RXZhbChzdGF0ZSk7XG59O1xuXG5wZXhwcnMuQXBwbHkucHJvdG90eXBlLmhhbmRsZUN5Y2xlID0gZnVuY3Rpb24gKHN0YXRlKSB7XG4gIGNvbnN0IHBvc0luZm8gPSBzdGF0ZS5nZXRDdXJyZW50UG9zSW5mbygpO1xuICBjb25zdCB7Y3VycmVudExlZnRSZWN1cnNpb259ID0gcG9zSW5mbztcbiAgY29uc3QgbWVtb0tleSA9IHRoaXMudG9NZW1vS2V5KCk7XG4gIGxldCBtZW1vUmVjID0gcG9zSW5mby5tZW1vW21lbW9LZXldO1xuXG4gIGlmIChjdXJyZW50TGVmdFJlY3Vyc2lvbiAmJiBjdXJyZW50TGVmdFJlY3Vyc2lvbi5oZWFkQXBwbGljYXRpb24udG9NZW1vS2V5KCkgPT09IG1lbW9LZXkpIHtcbiAgICAvLyBXZSBhbHJlYWR5IGtub3cgYWJvdXQgdGhpcyBsZWZ0IHJlY3Vyc2lvbiwgYnV0IGl0J3MgcG9zc2libGUgdGhlcmUgYXJlIFwiaW52b2x2ZWRcbiAgICAvLyBhcHBsaWNhdGlvbnNcIiB0aGF0IHdlIGRvbid0IGFscmVhZHkga25vdyBhYm91dCwgc28uLi5cbiAgICBtZW1vUmVjLnVwZGF0ZUludm9sdmVkQXBwbGljYXRpb25NZW1vS2V5cygpO1xuICB9IGVsc2UgaWYgKCFtZW1vUmVjKSB7XG4gICAgLy8gTmV3IGxlZnQgcmVjdXJzaW9uIGRldGVjdGVkISBNZW1vaXplIGEgZmFpbHVyZSB0byB0cnkgdG8gZ2V0IGEgc2VlZCBwYXJzZS5cbiAgICBtZW1vUmVjID0gcG9zSW5mby5tZW1vaXplKG1lbW9LZXksIHtcbiAgICAgIG1hdGNoTGVuZ3RoOiAwLFxuICAgICAgZXhhbWluZWRMZW5ndGg6IDAsXG4gICAgICB2YWx1ZTogZmFsc2UsXG4gICAgICByaWdodG1vc3RGYWlsdXJlT2Zmc2V0OiAtMSxcbiAgICB9KTtcbiAgICBwb3NJbmZvLnN0YXJ0TGVmdFJlY3Vyc2lvbih0aGlzLCBtZW1vUmVjKTtcbiAgfVxuICByZXR1cm4gc3RhdGUudXNlTWVtb2l6ZWRSZXN1bHQoc3RhdGUuaW5wdXRTdHJlYW0ucG9zLCBtZW1vUmVjKTtcbn07XG5cbnBleHBycy5BcHBseS5wcm90b3R5cGUucmVhbGx5RXZhbCA9IGZ1bmN0aW9uIChzdGF0ZSkge1xuICBjb25zdCB7aW5wdXRTdHJlYW19ID0gc3RhdGU7XG4gIGNvbnN0IG9yaWdQb3MgPSBpbnB1dFN0cmVhbS5wb3M7XG4gIGNvbnN0IG9yaWdQb3NJbmZvID0gc3RhdGUuZ2V0Q3VycmVudFBvc0luZm8oKTtcbiAgY29uc3QgcnVsZUluZm8gPSBzdGF0ZS5ncmFtbWFyLnJ1bGVzW3RoaXMucnVsZU5hbWVdO1xuICBjb25zdCB7Ym9keX0gPSBydWxlSW5mbztcbiAgY29uc3Qge2Rlc2NyaXB0aW9ufSA9IHJ1bGVJbmZvO1xuXG4gIHN0YXRlLmVudGVyQXBwbGljYXRpb24ob3JpZ1Bvc0luZm8sIHRoaXMpO1xuXG4gIGlmIChkZXNjcmlwdGlvbikge1xuICAgIHN0YXRlLnB1c2hGYWlsdXJlc0luZm8oKTtcbiAgfVxuXG4gIC8vIFJlc2V0IHRoZSBpbnB1dCBzdHJlYW0ncyBleGFtaW5lZExlbmd0aCBwcm9wZXJ0eSBzbyB0aGF0IHdlIGNhbiB0cmFja1xuICAvLyB0aGUgZXhhbWluZWQgbGVuZ3RoIG9mIHRoaXMgcGFydGljdWxhciBhcHBsaWNhdGlvbi5cbiAgY29uc3Qgb3JpZ0lucHV0U3RyZWFtRXhhbWluZWRMZW5ndGggPSBpbnB1dFN0cmVhbS5leGFtaW5lZExlbmd0aDtcbiAgaW5wdXRTdHJlYW0uZXhhbWluZWRMZW5ndGggPSAwO1xuXG4gIGxldCB2YWx1ZSA9IHRoaXMuZXZhbE9uY2UoYm9keSwgc3RhdGUpO1xuICBjb25zdCBjdXJyZW50TFIgPSBvcmlnUG9zSW5mby5jdXJyZW50TGVmdFJlY3Vyc2lvbjtcbiAgY29uc3QgbWVtb0tleSA9IHRoaXMudG9NZW1vS2V5KCk7XG4gIGNvbnN0IGlzSGVhZE9mTGVmdFJlY3Vyc2lvbiA9IGN1cnJlbnRMUiAmJiBjdXJyZW50TFIuaGVhZEFwcGxpY2F0aW9uLnRvTWVtb0tleSgpID09PSBtZW1vS2V5O1xuICBsZXQgbWVtb1JlYztcblxuICBpZiAoc3RhdGUuZG9Ob3RNZW1vaXplKSB7XG4gICAgc3RhdGUuZG9Ob3RNZW1vaXplID0gZmFsc2U7XG4gIH0gZWxzZSBpZiAoaXNIZWFkT2ZMZWZ0UmVjdXJzaW9uKSB7XG4gICAgdmFsdWUgPSB0aGlzLmdyb3dTZWVkUmVzdWx0KGJvZHksIHN0YXRlLCBvcmlnUG9zLCBjdXJyZW50TFIsIHZhbHVlKTtcbiAgICBvcmlnUG9zSW5mby5lbmRMZWZ0UmVjdXJzaW9uKCk7XG4gICAgbWVtb1JlYyA9IGN1cnJlbnRMUjtcbiAgICBtZW1vUmVjLmV4YW1pbmVkTGVuZ3RoID0gaW5wdXRTdHJlYW0uZXhhbWluZWRMZW5ndGggLSBvcmlnUG9zO1xuICAgIG1lbW9SZWMucmlnaHRtb3N0RmFpbHVyZU9mZnNldCA9IHN0YXRlLl9nZXRSaWdodG1vc3RGYWlsdXJlT2Zmc2V0KCk7XG4gICAgb3JpZ1Bvc0luZm8ubWVtb2l6ZShtZW1vS2V5LCBtZW1vUmVjKTsgLy8gdXBkYXRlcyBvcmlnUG9zSW5mbydzIG1heEV4YW1pbmVkTGVuZ3RoXG4gIH0gZWxzZSBpZiAoIWN1cnJlbnRMUiB8fCAhY3VycmVudExSLmlzSW52b2x2ZWQobWVtb0tleSkpIHtcbiAgICAvLyBUaGlzIGFwcGxpY2F0aW9uIGlzIG5vdCBpbnZvbHZlZCBpbiBsZWZ0IHJlY3Vyc2lvbiwgc28gaXQncyBvayB0byBtZW1vaXplIGl0LlxuICAgIG1lbW9SZWMgPSBvcmlnUG9zSW5mby5tZW1vaXplKG1lbW9LZXksIHtcbiAgICAgIG1hdGNoTGVuZ3RoOiBpbnB1dFN0cmVhbS5wb3MgLSBvcmlnUG9zLFxuICAgICAgZXhhbWluZWRMZW5ndGg6IGlucHV0U3RyZWFtLmV4YW1pbmVkTGVuZ3RoIC0gb3JpZ1BvcyxcbiAgICAgIHZhbHVlLFxuICAgICAgZmFpbHVyZXNBdFJpZ2h0bW9zdFBvc2l0aW9uOiBzdGF0ZS5jbG9uZVJlY29yZGVkRmFpbHVyZXMoKSxcbiAgICAgIHJpZ2h0bW9zdEZhaWx1cmVPZmZzZXQ6IHN0YXRlLl9nZXRSaWdodG1vc3RGYWlsdXJlT2Zmc2V0KCksXG4gICAgfSk7XG4gIH1cbiAgY29uc3Qgc3VjY2VlZGVkID0gISF2YWx1ZTtcblxuICBpZiAoZGVzY3JpcHRpb24pIHtcbiAgICBzdGF0ZS5wb3BGYWlsdXJlc0luZm8oKTtcbiAgICBpZiAoIXN1Y2NlZWRlZCkge1xuICAgICAgc3RhdGUucHJvY2Vzc0ZhaWx1cmUob3JpZ1BvcywgdGhpcyk7XG4gICAgfVxuICAgIGlmIChtZW1vUmVjKSB7XG4gICAgICBtZW1vUmVjLmZhaWx1cmVzQXRSaWdodG1vc3RQb3NpdGlvbiA9IHN0YXRlLmNsb25lUmVjb3JkZWRGYWlsdXJlcygpO1xuICAgICAgbWVtb1JlYy5yaWdodG1vc3RGYWlsdXJlT2Zmc2V0ID0gc3RhdGUuX2dldFJpZ2h0bW9zdEZhaWx1cmVPZmZzZXQoKTtcbiAgICB9XG4gIH1cblxuICAvLyBSZWNvcmQgdHJhY2UgaW5mb3JtYXRpb24gaW4gdGhlIG1lbW8gdGFibGUsIHNvIHRoYXQgaXQgaXMgYXZhaWxhYmxlIGlmIHRoZSBtZW1vaXplZCByZXN1bHRcbiAgLy8gaXMgdXNlZCBsYXRlci5cbiAgaWYgKHN0YXRlLmlzVHJhY2luZygpICYmIG1lbW9SZWMpIHtcbiAgICBjb25zdCBlbnRyeSA9IHN0YXRlLmdldFRyYWNlRW50cnkob3JpZ1BvcywgdGhpcywgc3VjY2VlZGVkLCBzdWNjZWVkZWQgPyBbdmFsdWVdIDogW10pO1xuICAgIGlmIChpc0hlYWRPZkxlZnRSZWN1cnNpb24pIHtcbiAgICAgIGNvbW1vbi5hc3NlcnQoZW50cnkudGVybWluYXRpbmdMUkVudHJ5ICE9IG51bGwgfHwgIXN1Y2NlZWRlZCk7XG4gICAgICBlbnRyeS5pc0hlYWRPZkxlZnRSZWN1cnNpb24gPSB0cnVlO1xuICAgIH1cbiAgICBtZW1vUmVjLnRyYWNlRW50cnkgPSBlbnRyeTtcbiAgfVxuXG4gIC8vIEZpeCB0aGUgaW5wdXQgc3RyZWFtJ3MgZXhhbWluZWRMZW5ndGggLS0gaXQgc2hvdWxkIGJlIHRoZSBtYXhpbXVtIGV4YW1pbmVkIGxlbmd0aFxuICAvLyBhY3Jvc3MgYWxsIGFwcGxpY2F0aW9ucywgbm90IGp1c3QgdGhpcyBvbmUuXG4gIGlucHV0U3RyZWFtLmV4YW1pbmVkTGVuZ3RoID0gTWF0aC5tYXgoXG4gICAgaW5wdXRTdHJlYW0uZXhhbWluZWRMZW5ndGgsXG4gICAgb3JpZ0lucHV0U3RyZWFtRXhhbWluZWRMZW5ndGhcbiAgKTtcblxuICBzdGF0ZS5leGl0QXBwbGljYXRpb24ob3JpZ1Bvc0luZm8sIHZhbHVlKTtcblxuICByZXR1cm4gc3VjY2VlZGVkO1xufTtcblxucGV4cHJzLkFwcGx5LnByb3RvdHlwZS5ldmFsT25jZSA9IGZ1bmN0aW9uIChleHByLCBzdGF0ZSkge1xuICBjb25zdCB7aW5wdXRTdHJlYW19ID0gc3RhdGU7XG4gIGNvbnN0IG9yaWdQb3MgPSBpbnB1dFN0cmVhbS5wb3M7XG5cbiAgaWYgKHN0YXRlLmV2YWwoZXhwcikpIHtcbiAgICBjb25zdCBhcml0eSA9IGV4cHIuZ2V0QXJpdHkoKTtcbiAgICBjb25zdCBiaW5kaW5ncyA9IHN0YXRlLl9iaW5kaW5ncy5zcGxpY2Uoc3RhdGUuX2JpbmRpbmdzLmxlbmd0aCAtIGFyaXR5LCBhcml0eSk7XG4gICAgY29uc3Qgb2Zmc2V0cyA9IHN0YXRlLl9iaW5kaW5nT2Zmc2V0cy5zcGxpY2Uoc3RhdGUuX2JpbmRpbmdPZmZzZXRzLmxlbmd0aCAtIGFyaXR5LCBhcml0eSk7XG4gICAgY29uc3QgbWF0Y2hMZW5ndGggPSBpbnB1dFN0cmVhbS5wb3MgLSBvcmlnUG9zO1xuICAgIHJldHVybiBuZXcgTm9udGVybWluYWxOb2RlKHRoaXMucnVsZU5hbWUsIGJpbmRpbmdzLCBvZmZzZXRzLCBtYXRjaExlbmd0aCk7XG4gIH0gZWxzZSB7XG4gICAgcmV0dXJuIGZhbHNlO1xuICB9XG59O1xuXG5wZXhwcnMuQXBwbHkucHJvdG90eXBlLmdyb3dTZWVkUmVzdWx0ID0gZnVuY3Rpb24gKGJvZHksIHN0YXRlLCBvcmlnUG9zLCBsck1lbW9SZWMsIG5ld1ZhbHVlKSB7XG4gIGlmICghbmV3VmFsdWUpIHtcbiAgICByZXR1cm4gZmFsc2U7XG4gIH1cblxuICBjb25zdCB7aW5wdXRTdHJlYW19ID0gc3RhdGU7XG5cbiAgd2hpbGUgKHRydWUpIHtcbiAgICBsck1lbW9SZWMubWF0Y2hMZW5ndGggPSBpbnB1dFN0cmVhbS5wb3MgLSBvcmlnUG9zO1xuICAgIGxyTWVtb1JlYy52YWx1ZSA9IG5ld1ZhbHVlO1xuICAgIGxyTWVtb1JlYy5mYWlsdXJlc0F0UmlnaHRtb3N0UG9zaXRpb24gPSBzdGF0ZS5jbG9uZVJlY29yZGVkRmFpbHVyZXMoKTtcblxuICAgIGlmIChzdGF0ZS5pc1RyYWNpbmcoKSkge1xuICAgICAgLy8gQmVmb3JlIGV2YWx1YXRpbmcgdGhlIGJvZHkgYWdhaW4sIGFkZCBhIHRyYWNlIG5vZGUgZm9yIHRoaXMgYXBwbGljYXRpb24gdG8gdGhlIG1lbW8gZW50cnkuXG4gICAgICAvLyBJdHMgb25seSBjaGlsZCBpcyBhIGNvcHkgb2YgdGhlIHRyYWNlIG5vZGUgZnJvbSBgbmV3VmFsdWVgLCB3aGljaCB3aWxsIGFsd2F5cyBiZSB0aGUgbGFzdFxuICAgICAgLy8gZWxlbWVudCBpbiBgc3RhdGUudHJhY2VgLlxuICAgICAgY29uc3Qgc2VlZFRyYWNlID0gc3RhdGUudHJhY2Vbc3RhdGUudHJhY2UubGVuZ3RoIC0gMV07XG4gICAgICBsck1lbW9SZWMudHJhY2VFbnRyeSA9IG5ldyBUcmFjZShcbiAgICAgICAgc3RhdGUuaW5wdXQsXG4gICAgICAgIG9yaWdQb3MsXG4gICAgICAgIGlucHV0U3RyZWFtLnBvcyxcbiAgICAgICAgdGhpcyxcbiAgICAgICAgdHJ1ZSxcbiAgICAgICAgW25ld1ZhbHVlXSxcbiAgICAgICAgW3NlZWRUcmFjZS5jbG9uZSgpXVxuICAgICAgKTtcbiAgICB9XG4gICAgaW5wdXRTdHJlYW0ucG9zID0gb3JpZ1BvcztcbiAgICBuZXdWYWx1ZSA9IHRoaXMuZXZhbE9uY2UoYm9keSwgc3RhdGUpO1xuICAgIGlmIChpbnB1dFN0cmVhbS5wb3MgLSBvcmlnUG9zIDw9IGxyTWVtb1JlYy5tYXRjaExlbmd0aCkge1xuICAgICAgYnJlYWs7XG4gICAgfVxuICAgIGlmIChzdGF0ZS5pc1RyYWNpbmcoKSkge1xuICAgICAgc3RhdGUudHJhY2Uuc3BsaWNlKC0yLCAxKTsgLy8gRHJvcCB0aGUgdHJhY2UgZm9yIHRoZSBvbGQgc2VlZC5cbiAgICB9XG4gIH1cbiAgaWYgKHN0YXRlLmlzVHJhY2luZygpKSB7XG4gICAgLy8gVGhlIGxhc3QgZW50cnkgaXMgZm9yIGFuIHVudXNlZCByZXN1bHQgLS0gcG9wIGl0IGFuZCBzYXZlIGl0IGluIHRoZSBcInJlYWxcIiBlbnRyeS5cbiAgICBsck1lbW9SZWMudHJhY2VFbnRyeS5yZWNvcmRMUlRlcm1pbmF0aW9uKHN0YXRlLnRyYWNlLnBvcCgpLCBuZXdWYWx1ZSk7XG4gIH1cbiAgaW5wdXRTdHJlYW0ucG9zID0gb3JpZ1BvcyArIGxyTWVtb1JlYy5tYXRjaExlbmd0aDtcbiAgcmV0dXJuIGxyTWVtb1JlYy52YWx1ZTtcbn07XG5cbnBleHBycy5Vbmljb2RlQ2hhci5wcm90b3R5cGUuZXZhbCA9IGZ1bmN0aW9uIChzdGF0ZSkge1xuICBjb25zdCB7aW5wdXRTdHJlYW19ID0gc3RhdGU7XG4gIGNvbnN0IG9yaWdQb3MgPSBpbnB1dFN0cmVhbS5wb3M7XG4gIGNvbnN0IGNwID0gaW5wdXRTdHJlYW0ubmV4dENvZGVQb2ludCgpO1xuICBpZiAoY3AgIT09IHVuZGVmaW5lZCAmJiBjcCA8PSBNQVhfQ09ERV9QT0lOVCkge1xuICAgIGNvbnN0IGNoID0gU3RyaW5nLmZyb21Db2RlUG9pbnQoY3ApO1xuICAgIGlmICh0aGlzLnBhdHRlcm4udGVzdChjaCkpIHtcbiAgICAgIHN0YXRlLnB1c2hCaW5kaW5nKG5ldyBUZXJtaW5hbE5vZGUoY2gubGVuZ3RoKSwgb3JpZ1Bvcyk7XG4gICAgICByZXR1cm4gdHJ1ZTtcbiAgICB9XG4gIH1cbiAgc3RhdGUucHJvY2Vzc0ZhaWx1cmUob3JpZ1BvcywgdGhpcyk7XG4gIHJldHVybiBmYWxzZTtcbn07XG4iLCJpbXBvcnQge2Fic3RyYWN0fSBmcm9tICcuL2NvbW1vbi5qcyc7XG5pbXBvcnQgKiBhcyBwZXhwcnMgZnJvbSAnLi9wZXhwcnMtbWFpbi5qcyc7XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG4vLyBPcGVyYXRpb25zXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuXG5wZXhwcnMuUEV4cHIucHJvdG90eXBlLmdldEFyaXR5ID0gYWJzdHJhY3QoJ2dldEFyaXR5Jyk7XG5cbnBleHBycy5hbnkuZ2V0QXJpdHkgPVxuICBwZXhwcnMuZW5kLmdldEFyaXR5ID1cbiAgcGV4cHJzLlRlcm1pbmFsLnByb3RvdHlwZS5nZXRBcml0eSA9XG4gIHBleHBycy5SYW5nZS5wcm90b3R5cGUuZ2V0QXJpdHkgPVxuICBwZXhwcnMuUGFyYW0ucHJvdG90eXBlLmdldEFyaXR5ID1cbiAgcGV4cHJzLkFwcGx5LnByb3RvdHlwZS5nZXRBcml0eSA9XG4gIHBleHBycy5Vbmljb2RlQ2hhci5wcm90b3R5cGUuZ2V0QXJpdHkgPVxuICAgIGZ1bmN0aW9uICgpIHtcbiAgICAgIHJldHVybiAxO1xuICAgIH07XG5cbnBleHBycy5BbHQucHJvdG90eXBlLmdldEFyaXR5ID0gZnVuY3Rpb24gKCkge1xuICAvLyBUaGlzIGlzIG9rIGIvYyBhbGwgdGVybXMgbXVzdCBoYXZlIHRoZSBzYW1lIGFyaXR5IC0tIHRoaXMgcHJvcGVydHkgaXNcbiAgLy8gY2hlY2tlZCBieSB0aGUgR3JhbW1hciBjb25zdHJ1Y3Rvci5cbiAgcmV0dXJuIHRoaXMudGVybXMubGVuZ3RoID09PSAwID8gMCA6IHRoaXMudGVybXNbMF0uZ2V0QXJpdHkoKTtcbn07XG5cbnBleHBycy5TZXEucHJvdG90eXBlLmdldEFyaXR5ID0gZnVuY3Rpb24gKCkge1xuICBsZXQgYXJpdHkgPSAwO1xuICBmb3IgKGxldCBpZHggPSAwOyBpZHggPCB0aGlzLmZhY3RvcnMubGVuZ3RoOyBpZHgrKykge1xuICAgIGFyaXR5ICs9IHRoaXMuZmFjdG9yc1tpZHhdLmdldEFyaXR5KCk7XG4gIH1cbiAgcmV0dXJuIGFyaXR5O1xufTtcblxucGV4cHJzLkl0ZXIucHJvdG90eXBlLmdldEFyaXR5ID0gZnVuY3Rpb24gKCkge1xuICByZXR1cm4gdGhpcy5leHByLmdldEFyaXR5KCk7XG59O1xuXG5wZXhwcnMuTm90LnByb3RvdHlwZS5nZXRBcml0eSA9IGZ1bmN0aW9uICgpIHtcbiAgcmV0dXJuIDA7XG59O1xuXG5wZXhwcnMuTG9va2FoZWFkLnByb3RvdHlwZS5nZXRBcml0eSA9IHBleHBycy5MZXgucHJvdG90eXBlLmdldEFyaXR5ID0gZnVuY3Rpb24gKCkge1xuICByZXR1cm4gdGhpcy5leHByLmdldEFyaXR5KCk7XG59O1xuIiwiaW1wb3J0IHthYnN0cmFjdH0gZnJvbSAnLi9jb21tb24uanMnO1xuaW1wb3J0ICogYXMgcGV4cHJzIGZyb20gJy4vcGV4cHJzLW1haW4uanMnO1xuXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gUHJpdmF0ZSBzdHVmZlxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cblxuZnVuY3Rpb24gZ2V0TWV0YUluZm8oZXhwciwgZ3JhbW1hckludGVydmFsKSB7XG4gIGNvbnN0IG1ldGFJbmZvID0ge307XG4gIGlmIChleHByLnNvdXJjZSAmJiBncmFtbWFySW50ZXJ2YWwpIHtcbiAgICBjb25zdCBhZGp1c3RlZCA9IGV4cHIuc291cmNlLnJlbGF0aXZlVG8oZ3JhbW1hckludGVydmFsKTtcbiAgICBtZXRhSW5mby5zb3VyY2VJbnRlcnZhbCA9IFthZGp1c3RlZC5zdGFydElkeCwgYWRqdXN0ZWQuZW5kSWR4XTtcbiAgfVxuICByZXR1cm4gbWV0YUluZm87XG59XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG4vLyBPcGVyYXRpb25zXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuXG5wZXhwcnMuUEV4cHIucHJvdG90eXBlLm91dHB1dFJlY2lwZSA9IGFic3RyYWN0KCdvdXRwdXRSZWNpcGUnKTtcblxucGV4cHJzLmFueS5vdXRwdXRSZWNpcGUgPSBmdW5jdGlvbiAoZm9ybWFscywgZ3JhbW1hckludGVydmFsKSB7XG4gIHJldHVybiBbJ2FueScsIGdldE1ldGFJbmZvKHRoaXMsIGdyYW1tYXJJbnRlcnZhbCldO1xufTtcblxucGV4cHJzLmVuZC5vdXRwdXRSZWNpcGUgPSBmdW5jdGlvbiAoZm9ybWFscywgZ3JhbW1hckludGVydmFsKSB7XG4gIHJldHVybiBbJ2VuZCcsIGdldE1ldGFJbmZvKHRoaXMsIGdyYW1tYXJJbnRlcnZhbCldO1xufTtcblxucGV4cHJzLlRlcm1pbmFsLnByb3RvdHlwZS5vdXRwdXRSZWNpcGUgPSBmdW5jdGlvbiAoZm9ybWFscywgZ3JhbW1hckludGVydmFsKSB7XG4gIHJldHVybiBbJ3Rlcm1pbmFsJywgZ2V0TWV0YUluZm8odGhpcywgZ3JhbW1hckludGVydmFsKSwgdGhpcy5vYmpdO1xufTtcblxucGV4cHJzLlJhbmdlLnByb3RvdHlwZS5vdXRwdXRSZWNpcGUgPSBmdW5jdGlvbiAoZm9ybWFscywgZ3JhbW1hckludGVydmFsKSB7XG4gIHJldHVybiBbJ3JhbmdlJywgZ2V0TWV0YUluZm8odGhpcywgZ3JhbW1hckludGVydmFsKSwgdGhpcy5mcm9tLCB0aGlzLnRvXTtcbn07XG5cbnBleHBycy5QYXJhbS5wcm90b3R5cGUub3V0cHV0UmVjaXBlID0gZnVuY3Rpb24gKGZvcm1hbHMsIGdyYW1tYXJJbnRlcnZhbCkge1xuICByZXR1cm4gWydwYXJhbScsIGdldE1ldGFJbmZvKHRoaXMsIGdyYW1tYXJJbnRlcnZhbCksIHRoaXMuaW5kZXhdO1xufTtcblxucGV4cHJzLkFsdC5wcm90b3R5cGUub3V0cHV0UmVjaXBlID0gZnVuY3Rpb24gKGZvcm1hbHMsIGdyYW1tYXJJbnRlcnZhbCkge1xuICByZXR1cm4gWydhbHQnLCBnZXRNZXRhSW5mbyh0aGlzLCBncmFtbWFySW50ZXJ2YWwpXS5jb25jYXQoXG4gICAgdGhpcy50ZXJtcy5tYXAodGVybSA9PiB0ZXJtLm91dHB1dFJlY2lwZShmb3JtYWxzLCBncmFtbWFySW50ZXJ2YWwpKVxuICApO1xufTtcblxucGV4cHJzLkV4dGVuZC5wcm90b3R5cGUub3V0cHV0UmVjaXBlID0gZnVuY3Rpb24gKGZvcm1hbHMsIGdyYW1tYXJJbnRlcnZhbCkge1xuICBjb25zdCBleHRlbnNpb24gPSB0aGlzLnRlcm1zWzBdOyAvLyBbZXh0ZW5zaW9uLCBvcmlnaW5hbF1cbiAgcmV0dXJuIGV4dGVuc2lvbi5vdXRwdXRSZWNpcGUoZm9ybWFscywgZ3JhbW1hckludGVydmFsKTtcbn07XG5cbnBleHBycy5TcGxpY2UucHJvdG90eXBlLm91dHB1dFJlY2lwZSA9IGZ1bmN0aW9uIChmb3JtYWxzLCBncmFtbWFySW50ZXJ2YWwpIHtcbiAgY29uc3QgYmVmb3JlVGVybXMgPSB0aGlzLnRlcm1zLnNsaWNlKDAsIHRoaXMuZXhwYW5zaW9uUG9zKTtcbiAgY29uc3QgYWZ0ZXJUZXJtcyA9IHRoaXMudGVybXMuc2xpY2UodGhpcy5leHBhbnNpb25Qb3MgKyAxKTtcbiAgcmV0dXJuIFtcbiAgICAnc3BsaWNlJyxcbiAgICBnZXRNZXRhSW5mbyh0aGlzLCBncmFtbWFySW50ZXJ2YWwpLFxuICAgIGJlZm9yZVRlcm1zLm1hcCh0ZXJtID0+IHRlcm0ub3V0cHV0UmVjaXBlKGZvcm1hbHMsIGdyYW1tYXJJbnRlcnZhbCkpLFxuICAgIGFmdGVyVGVybXMubWFwKHRlcm0gPT4gdGVybS5vdXRwdXRSZWNpcGUoZm9ybWFscywgZ3JhbW1hckludGVydmFsKSksXG4gIF07XG59O1xuXG5wZXhwcnMuU2VxLnByb3RvdHlwZS5vdXRwdXRSZWNpcGUgPSBmdW5jdGlvbiAoZm9ybWFscywgZ3JhbW1hckludGVydmFsKSB7XG4gIHJldHVybiBbJ3NlcScsIGdldE1ldGFJbmZvKHRoaXMsIGdyYW1tYXJJbnRlcnZhbCldLmNvbmNhdChcbiAgICB0aGlzLmZhY3RvcnMubWFwKGZhY3RvciA9PiBmYWN0b3Iub3V0cHV0UmVjaXBlKGZvcm1hbHMsIGdyYW1tYXJJbnRlcnZhbCkpXG4gICk7XG59O1xuXG5wZXhwcnMuU3Rhci5wcm90b3R5cGUub3V0cHV0UmVjaXBlID1cbiAgcGV4cHJzLlBsdXMucHJvdG90eXBlLm91dHB1dFJlY2lwZSA9XG4gIHBleHBycy5PcHQucHJvdG90eXBlLm91dHB1dFJlY2lwZSA9XG4gIHBleHBycy5Ob3QucHJvdG90eXBlLm91dHB1dFJlY2lwZSA9XG4gIHBleHBycy5Mb29rYWhlYWQucHJvdG90eXBlLm91dHB1dFJlY2lwZSA9XG4gIHBleHBycy5MZXgucHJvdG90eXBlLm91dHB1dFJlY2lwZSA9XG4gICAgZnVuY3Rpb24gKGZvcm1hbHMsIGdyYW1tYXJJbnRlcnZhbCkge1xuICAgICAgcmV0dXJuIFtcbiAgICAgICAgdGhpcy5jb25zdHJ1Y3Rvci5uYW1lLnRvTG93ZXJDYXNlKCksXG4gICAgICAgIGdldE1ldGFJbmZvKHRoaXMsIGdyYW1tYXJJbnRlcnZhbCksXG4gICAgICAgIHRoaXMuZXhwci5vdXRwdXRSZWNpcGUoZm9ybWFscywgZ3JhbW1hckludGVydmFsKSxcbiAgICAgIF07XG4gICAgfTtcblxucGV4cHJzLkFwcGx5LnByb3RvdHlwZS5vdXRwdXRSZWNpcGUgPSBmdW5jdGlvbiAoZm9ybWFscywgZ3JhbW1hckludGVydmFsKSB7XG4gIHJldHVybiBbXG4gICAgJ2FwcCcsXG4gICAgZ2V0TWV0YUluZm8odGhpcywgZ3JhbW1hckludGVydmFsKSxcbiAgICB0aGlzLnJ1bGVOYW1lLFxuICAgIHRoaXMuYXJncy5tYXAoYXJnID0+IGFyZy5vdXRwdXRSZWNpcGUoZm9ybWFscywgZ3JhbW1hckludGVydmFsKSksXG4gIF07XG59O1xuXG5wZXhwcnMuVW5pY29kZUNoYXIucHJvdG90eXBlLm91dHB1dFJlY2lwZSA9IGZ1bmN0aW9uIChmb3JtYWxzLCBncmFtbWFySW50ZXJ2YWwpIHtcbiAgcmV0dXJuIFsndW5pY29kZUNoYXInLCBnZXRNZXRhSW5mbyh0aGlzLCBncmFtbWFySW50ZXJ2YWwpLCB0aGlzLmNhdGVnb3J5T3JQcm9wXTtcbn07XG4iLCJpbXBvcnQge2Fic3RyYWN0fSBmcm9tICcuL2NvbW1vbi5qcyc7XG5pbXBvcnQgKiBhcyBwZXhwcnMgZnJvbSAnLi9wZXhwcnMtbWFpbi5qcyc7XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG4vLyBPcGVyYXRpb25zXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuXG4vKlxuICBDYWxsZWQgYXQgZ3JhbW1hciBjcmVhdGlvbiB0aW1lIHRvIHJld3JpdGUgYSBydWxlIGJvZHksIHJlcGxhY2luZyBlYWNoIHJlZmVyZW5jZSB0byBhIGZvcm1hbFxuICBwYXJhbWV0ZXIgd2l0aCBhIGBQYXJhbWAgbm9kZS4gUmV0dXJucyBhIFBFeHByIC0tIGVpdGhlciBhIG5ldyBvbmUsIG9yIHRoZSBvcmlnaW5hbCBvbmUgaWZcbiAgaXQgd2FzIG1vZGlmaWVkIGluIHBsYWNlLlxuKi9cbnBleHBycy5QRXhwci5wcm90b3R5cGUuaW50cm9kdWNlUGFyYW1zID0gYWJzdHJhY3QoJ2ludHJvZHVjZVBhcmFtcycpO1xuXG5wZXhwcnMuYW55LmludHJvZHVjZVBhcmFtcyA9XG4gIHBleHBycy5lbmQuaW50cm9kdWNlUGFyYW1zID1cbiAgcGV4cHJzLlRlcm1pbmFsLnByb3RvdHlwZS5pbnRyb2R1Y2VQYXJhbXMgPVxuICBwZXhwcnMuUmFuZ2UucHJvdG90eXBlLmludHJvZHVjZVBhcmFtcyA9XG4gIHBleHBycy5QYXJhbS5wcm90b3R5cGUuaW50cm9kdWNlUGFyYW1zID1cbiAgcGV4cHJzLlVuaWNvZGVDaGFyLnByb3RvdHlwZS5pbnRyb2R1Y2VQYXJhbXMgPVxuICAgIGZ1bmN0aW9uIChmb3JtYWxzKSB7XG4gICAgICByZXR1cm4gdGhpcztcbiAgICB9O1xuXG5wZXhwcnMuQWx0LnByb3RvdHlwZS5pbnRyb2R1Y2VQYXJhbXMgPSBmdW5jdGlvbiAoZm9ybWFscykge1xuICB0aGlzLnRlcm1zLmZvckVhY2goKHRlcm0sIGlkeCwgdGVybXMpID0+IHtcbiAgICB0ZXJtc1tpZHhdID0gdGVybS5pbnRyb2R1Y2VQYXJhbXMoZm9ybWFscyk7XG4gIH0pO1xuICByZXR1cm4gdGhpcztcbn07XG5cbnBleHBycy5TZXEucHJvdG90eXBlLmludHJvZHVjZVBhcmFtcyA9IGZ1bmN0aW9uIChmb3JtYWxzKSB7XG4gIHRoaXMuZmFjdG9ycy5mb3JFYWNoKChmYWN0b3IsIGlkeCwgZmFjdG9ycykgPT4ge1xuICAgIGZhY3RvcnNbaWR4XSA9IGZhY3Rvci5pbnRyb2R1Y2VQYXJhbXMoZm9ybWFscyk7XG4gIH0pO1xuICByZXR1cm4gdGhpcztcbn07XG5cbnBleHBycy5JdGVyLnByb3RvdHlwZS5pbnRyb2R1Y2VQYXJhbXMgPVxuICBwZXhwcnMuTm90LnByb3RvdHlwZS5pbnRyb2R1Y2VQYXJhbXMgPVxuICBwZXhwcnMuTG9va2FoZWFkLnByb3RvdHlwZS5pbnRyb2R1Y2VQYXJhbXMgPVxuICBwZXhwcnMuTGV4LnByb3RvdHlwZS5pbnRyb2R1Y2VQYXJhbXMgPVxuICAgIGZ1bmN0aW9uIChmb3JtYWxzKSB7XG4gICAgICB0aGlzLmV4cHIgPSB0aGlzLmV4cHIuaW50cm9kdWNlUGFyYW1zKGZvcm1hbHMpO1xuICAgICAgcmV0dXJuIHRoaXM7XG4gICAgfTtcblxucGV4cHJzLkFwcGx5LnByb3RvdHlwZS5pbnRyb2R1Y2VQYXJhbXMgPSBmdW5jdGlvbiAoZm9ybWFscykge1xuICBjb25zdCBpbmRleCA9IGZvcm1hbHMuaW5kZXhPZih0aGlzLnJ1bGVOYW1lKTtcbiAgaWYgKGluZGV4ID49IDApIHtcbiAgICBpZiAodGhpcy5hcmdzLmxlbmd0aCA+IDApIHtcbiAgICAgIC8vIFRPRE86IFNob3VsZCB0aGlzIGJlIHN1cHBvcnRlZD8gU2VlIGlzc3VlICM2NC5cbiAgICAgIHRocm93IG5ldyBFcnJvcignUGFyYW1ldGVyaXplZCBydWxlcyBjYW5ub3QgYmUgcGFzc2VkIGFzIGFyZ3VtZW50cyB0byBhbm90aGVyIHJ1bGUuJyk7XG4gICAgfVxuICAgIHJldHVybiBuZXcgcGV4cHJzLlBhcmFtKGluZGV4KS53aXRoU291cmNlKHRoaXMuc291cmNlKTtcbiAgfSBlbHNlIHtcbiAgICB0aGlzLmFyZ3MuZm9yRWFjaCgoYXJnLCBpZHgsIGFyZ3MpID0+IHtcbiAgICAgIGFyZ3NbaWR4XSA9IGFyZy5pbnRyb2R1Y2VQYXJhbXMoZm9ybWFscyk7XG4gICAgfSk7XG4gICAgcmV0dXJuIHRoaXM7XG4gIH1cbn07XG4iLCJpbXBvcnQge2Fic3RyYWN0fSBmcm9tICcuL2NvbW1vbi5qcyc7XG5pbXBvcnQgKiBhcyBwZXhwcnMgZnJvbSAnLi9wZXhwcnMtbWFpbi5qcyc7XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG4vLyBPcGVyYXRpb25zXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuXG4vLyBSZXR1cm5zIGB0cnVlYCBpZiB0aGlzIHBhcnNpbmcgZXhwcmVzc2lvbiBtYXkgYWNjZXB0IHdpdGhvdXQgY29uc3VtaW5nIGFueSBpbnB1dC5cbnBleHBycy5QRXhwci5wcm90b3R5cGUuaXNOdWxsYWJsZSA9IGZ1bmN0aW9uIChncmFtbWFyKSB7XG4gIHJldHVybiB0aGlzLl9pc051bGxhYmxlKGdyYW1tYXIsIE9iamVjdC5jcmVhdGUobnVsbCkpO1xufTtcblxucGV4cHJzLlBFeHByLnByb3RvdHlwZS5faXNOdWxsYWJsZSA9IGFic3RyYWN0KCdfaXNOdWxsYWJsZScpO1xuXG5wZXhwcnMuYW55Ll9pc051bGxhYmxlID1cbiAgcGV4cHJzLlJhbmdlLnByb3RvdHlwZS5faXNOdWxsYWJsZSA9XG4gIHBleHBycy5QYXJhbS5wcm90b3R5cGUuX2lzTnVsbGFibGUgPVxuICBwZXhwcnMuUGx1cy5wcm90b3R5cGUuX2lzTnVsbGFibGUgPVxuICBwZXhwcnMuVW5pY29kZUNoYXIucHJvdG90eXBlLl9pc051bGxhYmxlID1cbiAgICBmdW5jdGlvbiAoZ3JhbW1hciwgbWVtbykge1xuICAgICAgcmV0dXJuIGZhbHNlO1xuICAgIH07XG5cbnBleHBycy5lbmQuX2lzTnVsbGFibGUgPSBmdW5jdGlvbiAoZ3JhbW1hciwgbWVtbykge1xuICByZXR1cm4gdHJ1ZTtcbn07XG5cbnBleHBycy5UZXJtaW5hbC5wcm90b3R5cGUuX2lzTnVsbGFibGUgPSBmdW5jdGlvbiAoZ3JhbW1hciwgbWVtbykge1xuICBpZiAodHlwZW9mIHRoaXMub2JqID09PSAnc3RyaW5nJykge1xuICAgIC8vIFRoaXMgaXMgYW4gb3Zlci1zaW1wbGlmaWNhdGlvbjogaXQncyBvbmx5IGNvcnJlY3QgaWYgdGhlIGlucHV0IGlzIGEgc3RyaW5nLiBJZiBpdCdzIGFuIGFycmF5XG4gICAgLy8gb3IgYW4gb2JqZWN0LCB0aGVuIHRoZSBlbXB0eSBzdHJpbmcgcGFyc2luZyBleHByZXNzaW9uIGlzIG5vdCBudWxsYWJsZS5cbiAgICByZXR1cm4gdGhpcy5vYmogPT09ICcnO1xuICB9IGVsc2Uge1xuICAgIHJldHVybiBmYWxzZTtcbiAgfVxufTtcblxucGV4cHJzLkFsdC5wcm90b3R5cGUuX2lzTnVsbGFibGUgPSBmdW5jdGlvbiAoZ3JhbW1hciwgbWVtbykge1xuICByZXR1cm4gdGhpcy50ZXJtcy5sZW5ndGggPT09IDAgfHwgdGhpcy50ZXJtcy5zb21lKHRlcm0gPT4gdGVybS5faXNOdWxsYWJsZShncmFtbWFyLCBtZW1vKSk7XG59O1xuXG5wZXhwcnMuU2VxLnByb3RvdHlwZS5faXNOdWxsYWJsZSA9IGZ1bmN0aW9uIChncmFtbWFyLCBtZW1vKSB7XG4gIHJldHVybiB0aGlzLmZhY3RvcnMuZXZlcnkoZmFjdG9yID0+IGZhY3Rvci5faXNOdWxsYWJsZShncmFtbWFyLCBtZW1vKSk7XG59O1xuXG5wZXhwcnMuU3Rhci5wcm90b3R5cGUuX2lzTnVsbGFibGUgPVxuICBwZXhwcnMuT3B0LnByb3RvdHlwZS5faXNOdWxsYWJsZSA9XG4gIHBleHBycy5Ob3QucHJvdG90eXBlLl9pc051bGxhYmxlID1cbiAgcGV4cHJzLkxvb2thaGVhZC5wcm90b3R5cGUuX2lzTnVsbGFibGUgPVxuICAgIGZ1bmN0aW9uIChncmFtbWFyLCBtZW1vKSB7XG4gICAgICByZXR1cm4gdHJ1ZTtcbiAgICB9O1xuXG5wZXhwcnMuTGV4LnByb3RvdHlwZS5faXNOdWxsYWJsZSA9IGZ1bmN0aW9uIChncmFtbWFyLCBtZW1vKSB7XG4gIHJldHVybiB0aGlzLmV4cHIuX2lzTnVsbGFibGUoZ3JhbW1hciwgbWVtbyk7XG59O1xuXG5wZXhwcnMuQXBwbHkucHJvdG90eXBlLl9pc051bGxhYmxlID0gZnVuY3Rpb24gKGdyYW1tYXIsIG1lbW8pIHtcbiAgY29uc3Qga2V5ID0gdGhpcy50b01lbW9LZXkoKTtcbiAgaWYgKCFPYmplY3QucHJvdG90eXBlLmhhc093blByb3BlcnR5LmNhbGwobWVtbywga2V5KSkge1xuICAgIGNvbnN0IHtib2R5fSA9IGdyYW1tYXIucnVsZXNbdGhpcy5ydWxlTmFtZV07XG4gICAgY29uc3QgaW5saW5lZCA9IGJvZHkuc3Vic3RpdHV0ZVBhcmFtcyh0aGlzLmFyZ3MpO1xuICAgIG1lbW9ba2V5XSA9IGZhbHNlOyAvLyBQcmV2ZW50IGluZmluaXRlIHJlY3Vyc2lvbiBmb3IgcmVjdXJzaXZlIHJ1bGVzLlxuICAgIG1lbW9ba2V5XSA9IGlubGluZWQuX2lzTnVsbGFibGUoZ3JhbW1hciwgbWVtbyk7XG4gIH1cbiAgcmV0dXJuIG1lbW9ba2V5XTtcbn07XG4iLCJpbXBvcnQge2Fic3RyYWN0LCBjaGVja05vdE51bGx9IGZyb20gJy4vY29tbW9uLmpzJztcbmltcG9ydCAqIGFzIHBleHBycyBmcm9tICcuL3BleHBycy1tYWluLmpzJztcblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cbi8vIE9wZXJhdGlvbnNcbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG5cbi8qXG4gIFJldHVybnMgYSBQRXhwciB0aGF0IHJlc3VsdHMgZnJvbSByZWN1cnNpdmVseSByZXBsYWNpbmcgZXZlcnkgZm9ybWFsIHBhcmFtZXRlciAoaS5lLiwgaW5zdGFuY2VcbiAgb2YgYFBhcmFtYCkgaW5zaWRlIHRoaXMgUEV4cHIgd2l0aCBpdHMgYWN0dWFsIHZhbHVlIGZyb20gYGFjdHVhbHNgIChhbiBBcnJheSkuXG5cbiAgVGhlIHJlY2VpdmVyIG11c3Qgbm90IGJlIG1vZGlmaWVkOyBhIG5ldyBQRXhwciBtdXN0IGJlIHJldHVybmVkIGlmIGFueSByZXBsYWNlbWVudCBpcyBuZWNlc3NhcnkuXG4qL1xuLy8gZnVuY3Rpb24oYWN0dWFscykgeyAuLi4gfVxucGV4cHJzLlBFeHByLnByb3RvdHlwZS5zdWJzdGl0dXRlUGFyYW1zID0gYWJzdHJhY3QoJ3N1YnN0aXR1dGVQYXJhbXMnKTtcblxucGV4cHJzLmFueS5zdWJzdGl0dXRlUGFyYW1zID1cbiAgcGV4cHJzLmVuZC5zdWJzdGl0dXRlUGFyYW1zID1cbiAgcGV4cHJzLlRlcm1pbmFsLnByb3RvdHlwZS5zdWJzdGl0dXRlUGFyYW1zID1cbiAgcGV4cHJzLlJhbmdlLnByb3RvdHlwZS5zdWJzdGl0dXRlUGFyYW1zID1cbiAgcGV4cHJzLlVuaWNvZGVDaGFyLnByb3RvdHlwZS5zdWJzdGl0dXRlUGFyYW1zID1cbiAgICBmdW5jdGlvbiAoYWN0dWFscykge1xuICAgICAgcmV0dXJuIHRoaXM7XG4gICAgfTtcblxucGV4cHJzLlBhcmFtLnByb3RvdHlwZS5zdWJzdGl0dXRlUGFyYW1zID0gZnVuY3Rpb24gKGFjdHVhbHMpIHtcbiAgcmV0dXJuIGNoZWNrTm90TnVsbChhY3R1YWxzW3RoaXMuaW5kZXhdKTtcbn07XG5cbnBleHBycy5BbHQucHJvdG90eXBlLnN1YnN0aXR1dGVQYXJhbXMgPSBmdW5jdGlvbiAoYWN0dWFscykge1xuICByZXR1cm4gbmV3IHBleHBycy5BbHQodGhpcy50ZXJtcy5tYXAodGVybSA9PiB0ZXJtLnN1YnN0aXR1dGVQYXJhbXMoYWN0dWFscykpKTtcbn07XG5cbnBleHBycy5TZXEucHJvdG90eXBlLnN1YnN0aXR1dGVQYXJhbXMgPSBmdW5jdGlvbiAoYWN0dWFscykge1xuICByZXR1cm4gbmV3IHBleHBycy5TZXEodGhpcy5mYWN0b3JzLm1hcChmYWN0b3IgPT4gZmFjdG9yLnN1YnN0aXR1dGVQYXJhbXMoYWN0dWFscykpKTtcbn07XG5cbnBleHBycy5JdGVyLnByb3RvdHlwZS5zdWJzdGl0dXRlUGFyYW1zID1cbiAgcGV4cHJzLk5vdC5wcm90b3R5cGUuc3Vic3RpdHV0ZVBhcmFtcyA9XG4gIHBleHBycy5Mb29rYWhlYWQucHJvdG90eXBlLnN1YnN0aXR1dGVQYXJhbXMgPVxuICBwZXhwcnMuTGV4LnByb3RvdHlwZS5zdWJzdGl0dXRlUGFyYW1zID1cbiAgICBmdW5jdGlvbiAoYWN0dWFscykge1xuICAgICAgcmV0dXJuIG5ldyB0aGlzLmNvbnN0cnVjdG9yKHRoaXMuZXhwci5zdWJzdGl0dXRlUGFyYW1zKGFjdHVhbHMpKTtcbiAgICB9O1xuXG5wZXhwcnMuQXBwbHkucHJvdG90eXBlLnN1YnN0aXR1dGVQYXJhbXMgPSBmdW5jdGlvbiAoYWN0dWFscykge1xuICBpZiAodGhpcy5hcmdzLmxlbmd0aCA9PT0gMCkge1xuICAgIC8vIEF2b2lkIG1ha2luZyBhIGNvcHkgb2YgdGhpcyBhcHBsaWNhdGlvbiwgYXMgYW4gb3B0aW1pemF0aW9uXG4gICAgcmV0dXJuIHRoaXM7XG4gIH0gZWxzZSB7XG4gICAgY29uc3QgYXJncyA9IHRoaXMuYXJncy5tYXAoYXJnID0+IGFyZy5zdWJzdGl0dXRlUGFyYW1zKGFjdHVhbHMpKTtcbiAgICByZXR1cm4gbmV3IHBleHBycy5BcHBseSh0aGlzLnJ1bGVOYW1lLCBhcmdzKTtcbiAgfVxufTtcbiIsImltcG9ydCB7YWJzdHJhY3QsIGNvcHlXaXRob3V0RHVwbGljYXRlc30gZnJvbSAnLi9jb21tb24uanMnO1xuaW1wb3J0ICogYXMgcGV4cHJzIGZyb20gJy4vcGV4cHJzLW1haW4uanMnO1xuXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gUHJpdmF0ZSBzdHVmZlxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cblxuZnVuY3Rpb24gaXNSZXN0cmljdGVkSlNJZGVudGlmaWVyKHN0cikge1xuICByZXR1cm4gL15bYS16QS1aXyRdWzAtOWEtekEtWl8kXSokLy50ZXN0KHN0cik7XG59XG5cbmZ1bmN0aW9uIHJlc29sdmVEdXBsaWNhdGVkTmFtZXMoYXJndW1lbnROYW1lTGlzdCkge1xuICAvLyBgY291bnRgIGlzIHVzZWQgdG8gcmVjb3JkIHRoZSBudW1iZXIgb2YgdGltZXMgZWFjaCBhcmd1bWVudCBuYW1lIG9jY3VycyBpbiB0aGUgbGlzdCxcbiAgLy8gdGhpcyBpcyB1c2VmdWwgZm9yIGNoZWNraW5nIGR1cGxpY2F0ZWQgYXJndW1lbnQgbmFtZS4gSXQgbWFwcyBhcmd1bWVudCBuYW1lcyB0byBpbnRzLlxuICBjb25zdCBjb3VudCA9IE9iamVjdC5jcmVhdGUobnVsbCk7XG4gIGFyZ3VtZW50TmFtZUxpc3QuZm9yRWFjaChhcmdOYW1lID0+IHtcbiAgICBjb3VudFthcmdOYW1lXSA9IChjb3VudFthcmdOYW1lXSB8fCAwKSArIDE7XG4gIH0pO1xuXG4gIC8vIEFwcGVuZCBzdWJzY3JpcHRzICgnXzEnLCAnXzInLCAuLi4pIHRvIGR1cGxpY2F0ZSBhcmd1bWVudCBuYW1lcy5cbiAgT2JqZWN0LmtleXMoY291bnQpLmZvckVhY2goZHVwQXJnTmFtZSA9PiB7XG4gICAgaWYgKGNvdW50W2R1cEFyZ05hbWVdIDw9IDEpIHtcbiAgICAgIHJldHVybjtcbiAgICB9XG5cbiAgICAvLyBUaGlzIG5hbWUgc2hvd3MgdXAgbW9yZSB0aGFuIG9uY2UsIHNvIGFkZCBzdWJzY3JpcHRzLlxuICAgIGxldCBzdWJzY3JpcHQgPSAxO1xuICAgIGFyZ3VtZW50TmFtZUxpc3QuZm9yRWFjaCgoYXJnTmFtZSwgaWR4KSA9PiB7XG4gICAgICBpZiAoYXJnTmFtZSA9PT0gZHVwQXJnTmFtZSkge1xuICAgICAgICBhcmd1bWVudE5hbWVMaXN0W2lkeF0gPSBhcmdOYW1lICsgJ18nICsgc3Vic2NyaXB0Kys7XG4gICAgICB9XG4gICAgfSk7XG4gIH0pO1xufVxuXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gT3BlcmF0aW9uc1xuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cblxuLypcbiAgUmV0dXJucyBhIGxpc3Qgb2Ygc3RyaW5ncyB0aGF0IHdpbGwgYmUgdXNlZCBhcyB0aGUgZGVmYXVsdCBhcmd1bWVudCBuYW1lcyBmb3IgaXRzIHJlY2VpdmVyXG4gIChhIHBleHByKSBpbiBhIHNlbWFudGljIGFjdGlvbi4gVGhpcyBpcyB1c2VkIGV4Y2x1c2l2ZWx5IGJ5IHRoZSBTZW1hbnRpY3MgRWRpdG9yLlxuXG4gIGBmaXJzdEFyZ0luZGV4YCBpcyB0aGUgMS1iYXNlZCBpbmRleCBvZiB0aGUgZmlyc3QgYXJndW1lbnQgbmFtZSB0aGF0IHdpbGwgYmUgZ2VuZXJhdGVkIGZvciB0aGlzXG4gIHBleHByLiBJdCBlbmFibGVzIHVzIHRvIG5hbWUgYXJndW1lbnRzIHBvc2l0aW9uYWxseSwgZS5nLiwgaWYgdGhlIHNlY29uZCBhcmd1bWVudCBpcyBhXG4gIG5vbi1hbHBoYW51bWVyaWMgdGVybWluYWwgbGlrZSBcIitcIiwgaXQgd2lsbCBiZSBuYW1lZCAnJDInLlxuXG4gIGBub0R1cENoZWNrYCBpcyB0cnVlIGlmIHRoZSBjYWxsZXIgb2YgYHRvQXJndW1lbnROYW1lTGlzdGAgaXMgbm90IGEgdG9wIGxldmVsIGNhbGxlci4gSXQgZW5hYmxlc1xuICB1cyB0byBhdm9pZCBuZXN0ZWQgZHVwbGljYXRpb24gc3Vic2NyaXB0cyBhcHBlbmRpbmcsIGUuZy4sICdfMV8xJywgJ18xXzInLCBieSBvbmx5IGNoZWNraW5nXG4gIGR1cGxpY2F0ZXMgYXQgdGhlIHRvcCBsZXZlbC5cblxuICBIZXJlIGlzIGEgbW9yZSBlbGFib3JhdGUgZXhhbXBsZSB0aGF0IGlsbHVzdHJhdGVzIGhvdyB0aGlzIG1ldGhvZCB3b3JrczpcbiAgYChhIFwiK1wiIGIpLnRvQXJndW1lbnROYW1lTGlzdCgxKWAgZXZhbHVhdGVzIHRvIGBbJ2EnLCAnJDInLCAnYiddYCB3aXRoIHRoZSBmb2xsb3dpbmcgcmVjdXJzaXZlXG4gIGNhbGxzOlxuXG4gICAgKGEpLnRvQXJndW1lbnROYW1lTGlzdCgxKSAtPiBbJ2EnXSxcbiAgICAoXCIrXCIpLnRvQXJndW1lbnROYW1lTGlzdCgyKSAtPiBbJyQyJ10sXG4gICAgKGIpLnRvQXJndW1lbnROYW1lTGlzdCgzKSAtPiBbJ2InXVxuXG4gIE5vdGVzOlxuICAqIFRoaXMgbWV0aG9kIG11c3Qgb25seSBiZSBjYWxsZWQgb24gd2VsbC1mb3JtZWQgZXhwcmVzc2lvbnMsIGUuZy4sIHRoZSByZWNlaXZlciBtdXN0XG4gICAgbm90IGhhdmUgYW55IEFsdCBzdWItZXhwcmVzc2lvbnMgd2l0aCBpbmNvbnNpc3RlbnQgYXJpdGllcy5cbiAgKiBlLmdldEFyaXR5KCkgPT09IGUudG9Bcmd1bWVudE5hbWVMaXN0KDEpLmxlbmd0aFxuKi9cbi8vIGZ1bmN0aW9uKGZpcnN0QXJnSW5kZXgsIG5vRHVwQ2hlY2spIHsgLi4uIH1cbnBleHBycy5QRXhwci5wcm90b3R5cGUudG9Bcmd1bWVudE5hbWVMaXN0ID0gYWJzdHJhY3QoJ3RvQXJndW1lbnROYW1lTGlzdCcpO1xuXG5wZXhwcnMuYW55LnRvQXJndW1lbnROYW1lTGlzdCA9IGZ1bmN0aW9uIChmaXJzdEFyZ0luZGV4LCBub0R1cENoZWNrKSB7XG4gIHJldHVybiBbJ2FueSddO1xufTtcblxucGV4cHJzLmVuZC50b0FyZ3VtZW50TmFtZUxpc3QgPSBmdW5jdGlvbiAoZmlyc3RBcmdJbmRleCwgbm9EdXBDaGVjaykge1xuICByZXR1cm4gWydlbmQnXTtcbn07XG5cbnBleHBycy5UZXJtaW5hbC5wcm90b3R5cGUudG9Bcmd1bWVudE5hbWVMaXN0ID0gZnVuY3Rpb24gKGZpcnN0QXJnSW5kZXgsIG5vRHVwQ2hlY2spIHtcbiAgaWYgKHR5cGVvZiB0aGlzLm9iaiA9PT0gJ3N0cmluZycgJiYgL15bX2EtekEtWjAtOV0rJC8udGVzdCh0aGlzLm9iaikpIHtcbiAgICAvLyBJZiB0aGlzIHRlcm1pbmFsIGlzIGEgdmFsaWQgc3VmZml4IGZvciBhIEpTIGlkZW50aWZpZXIsIGp1c3QgcHJlcGVuZCBpdCB3aXRoICdfJ1xuICAgIHJldHVybiBbJ18nICsgdGhpcy5vYmpdO1xuICB9IGVsc2Uge1xuICAgIC8vIE90aGVyd2lzZSwgbmFtZSBpdCBwb3NpdGlvbmFsbHkuXG4gICAgcmV0dXJuIFsnJCcgKyBmaXJzdEFyZ0luZGV4XTtcbiAgfVxufTtcblxucGV4cHJzLlJhbmdlLnByb3RvdHlwZS50b0FyZ3VtZW50TmFtZUxpc3QgPSBmdW5jdGlvbiAoZmlyc3RBcmdJbmRleCwgbm9EdXBDaGVjaykge1xuICBsZXQgYXJnTmFtZSA9IHRoaXMuZnJvbSArICdfdG9fJyArIHRoaXMudG87XG4gIC8vIElmIHRoZSBgYXJnTmFtZWAgaXMgbm90IHZhbGlkIHRoZW4gdHJ5IHRvIHByZXBlbmQgYSBgX2AuXG4gIGlmICghaXNSZXN0cmljdGVkSlNJZGVudGlmaWVyKGFyZ05hbWUpKSB7XG4gICAgYXJnTmFtZSA9ICdfJyArIGFyZ05hbWU7XG4gIH1cbiAgLy8gSWYgdGhlIGBhcmdOYW1lYCBzdGlsbCBub3QgdmFsaWQgYWZ0ZXIgcHJlcGVuZGluZyBhIGBfYCwgdGhlbiBuYW1lIGl0IHBvc2l0aW9uYWxseS5cbiAgaWYgKCFpc1Jlc3RyaWN0ZWRKU0lkZW50aWZpZXIoYXJnTmFtZSkpIHtcbiAgICBhcmdOYW1lID0gJyQnICsgZmlyc3RBcmdJbmRleDtcbiAgfVxuICByZXR1cm4gW2FyZ05hbWVdO1xufTtcblxucGV4cHJzLkFsdC5wcm90b3R5cGUudG9Bcmd1bWVudE5hbWVMaXN0ID0gZnVuY3Rpb24gKGZpcnN0QXJnSW5kZXgsIG5vRHVwQ2hlY2spIHtcbiAgLy8gYHRlcm1BcmdOYW1lTGlzdHNgIGlzIGFuIGFycmF5IG9mIGFycmF5cyB3aGVyZSBlYWNoIHJvdyBpcyB0aGVcbiAgLy8gYXJndW1lbnQgbmFtZSBsaXN0IHRoYXQgY29ycmVzcG9uZHMgdG8gYSB0ZXJtIGluIHRoaXMgYWx0ZXJuYXRpb24uXG4gIGNvbnN0IHRlcm1BcmdOYW1lTGlzdHMgPSB0aGlzLnRlcm1zLm1hcCh0ZXJtID0+XG4gICAgdGVybS50b0FyZ3VtZW50TmFtZUxpc3QoZmlyc3RBcmdJbmRleCwgdHJ1ZSlcbiAgKTtcblxuICBjb25zdCBhcmd1bWVudE5hbWVMaXN0ID0gW107XG4gIGNvbnN0IG51bUFyZ3MgPSB0ZXJtQXJnTmFtZUxpc3RzWzBdLmxlbmd0aDtcbiAgZm9yIChsZXQgY29sSWR4ID0gMDsgY29sSWR4IDwgbnVtQXJnczsgY29sSWR4KyspIHtcbiAgICBjb25zdCBjb2wgPSBbXTtcbiAgICBmb3IgKGxldCByb3dJZHggPSAwOyByb3dJZHggPCB0aGlzLnRlcm1zLmxlbmd0aDsgcm93SWR4KyspIHtcbiAgICAgIGNvbC5wdXNoKHRlcm1BcmdOYW1lTGlzdHNbcm93SWR4XVtjb2xJZHhdKTtcbiAgICB9XG4gICAgY29uc3QgdW5pcXVlTmFtZXMgPSBjb3B5V2l0aG91dER1cGxpY2F0ZXMoY29sKTtcbiAgICBhcmd1bWVudE5hbWVMaXN0LnB1c2godW5pcXVlTmFtZXMuam9pbignX29yXycpKTtcbiAgfVxuXG4gIGlmICghbm9EdXBDaGVjaykge1xuICAgIHJlc29sdmVEdXBsaWNhdGVkTmFtZXMoYXJndW1lbnROYW1lTGlzdCk7XG4gIH1cbiAgcmV0dXJuIGFyZ3VtZW50TmFtZUxpc3Q7XG59O1xuXG5wZXhwcnMuU2VxLnByb3RvdHlwZS50b0FyZ3VtZW50TmFtZUxpc3QgPSBmdW5jdGlvbiAoZmlyc3RBcmdJbmRleCwgbm9EdXBDaGVjaykge1xuICAvLyBHZW5lcmF0ZSB0aGUgYXJndW1lbnQgbmFtZSBsaXN0LCB3aXRob3V0IHdvcnJ5aW5nIGFib3V0IGR1cGxpY2F0ZXMuXG4gIGxldCBhcmd1bWVudE5hbWVMaXN0ID0gW107XG4gIHRoaXMuZmFjdG9ycy5mb3JFYWNoKGZhY3RvciA9PiB7XG4gICAgY29uc3QgZmFjdG9yQXJndW1lbnROYW1lTGlzdCA9IGZhY3Rvci50b0FyZ3VtZW50TmFtZUxpc3QoZmlyc3RBcmdJbmRleCwgdHJ1ZSk7XG4gICAgYXJndW1lbnROYW1lTGlzdCA9IGFyZ3VtZW50TmFtZUxpc3QuY29uY2F0KGZhY3RvckFyZ3VtZW50TmFtZUxpc3QpO1xuXG4gICAgLy8gU2hpZnQgdGhlIGZpcnN0QXJnSW5kZXggdG8gdGFrZSB0aGlzIGZhY3RvcidzIGFyZ3VtZW50IG5hbWVzIGludG8gYWNjb3VudC5cbiAgICBmaXJzdEFyZ0luZGV4ICs9IGZhY3RvckFyZ3VtZW50TmFtZUxpc3QubGVuZ3RoO1xuICB9KTtcbiAgaWYgKCFub0R1cENoZWNrKSB7XG4gICAgcmVzb2x2ZUR1cGxpY2F0ZWROYW1lcyhhcmd1bWVudE5hbWVMaXN0KTtcbiAgfVxuICByZXR1cm4gYXJndW1lbnROYW1lTGlzdDtcbn07XG5cbnBleHBycy5JdGVyLnByb3RvdHlwZS50b0FyZ3VtZW50TmFtZUxpc3QgPSBmdW5jdGlvbiAoZmlyc3RBcmdJbmRleCwgbm9EdXBDaGVjaykge1xuICBjb25zdCBhcmd1bWVudE5hbWVMaXN0ID0gdGhpcy5leHByXG4gICAgLnRvQXJndW1lbnROYW1lTGlzdChmaXJzdEFyZ0luZGV4LCBub0R1cENoZWNrKVxuICAgIC5tYXAoZXhwckFyZ3VtZW50U3RyaW5nID0+XG4gICAgICBleHByQXJndW1lbnRTdHJpbmdbZXhwckFyZ3VtZW50U3RyaW5nLmxlbmd0aCAtIDFdID09PSAncydcbiAgICAgICAgPyBleHByQXJndW1lbnRTdHJpbmcgKyAnZXMnXG4gICAgICAgIDogZXhwckFyZ3VtZW50U3RyaW5nICsgJ3MnXG4gICAgKTtcbiAgaWYgKCFub0R1cENoZWNrKSB7XG4gICAgcmVzb2x2ZUR1cGxpY2F0ZWROYW1lcyhhcmd1bWVudE5hbWVMaXN0KTtcbiAgfVxuICByZXR1cm4gYXJndW1lbnROYW1lTGlzdDtcbn07XG5cbnBleHBycy5PcHQucHJvdG90eXBlLnRvQXJndW1lbnROYW1lTGlzdCA9IGZ1bmN0aW9uIChmaXJzdEFyZ0luZGV4LCBub0R1cENoZWNrKSB7XG4gIHJldHVybiB0aGlzLmV4cHIudG9Bcmd1bWVudE5hbWVMaXN0KGZpcnN0QXJnSW5kZXgsIG5vRHVwQ2hlY2spLm1hcChhcmdOYW1lID0+IHtcbiAgICByZXR1cm4gJ29wdCcgKyBhcmdOYW1lWzBdLnRvVXBwZXJDYXNlKCkgKyBhcmdOYW1lLnNsaWNlKDEpO1xuICB9KTtcbn07XG5cbnBleHBycy5Ob3QucHJvdG90eXBlLnRvQXJndW1lbnROYW1lTGlzdCA9IGZ1bmN0aW9uIChmaXJzdEFyZ0luZGV4LCBub0R1cENoZWNrKSB7XG4gIHJldHVybiBbXTtcbn07XG5cbnBleHBycy5Mb29rYWhlYWQucHJvdG90eXBlLnRvQXJndW1lbnROYW1lTGlzdCA9IHBleHBycy5MZXgucHJvdG90eXBlLnRvQXJndW1lbnROYW1lTGlzdCA9XG4gIGZ1bmN0aW9uIChmaXJzdEFyZ0luZGV4LCBub0R1cENoZWNrKSB7XG4gICAgcmV0dXJuIHRoaXMuZXhwci50b0FyZ3VtZW50TmFtZUxpc3QoZmlyc3RBcmdJbmRleCwgbm9EdXBDaGVjayk7XG4gIH07XG5cbnBleHBycy5BcHBseS5wcm90b3R5cGUudG9Bcmd1bWVudE5hbWVMaXN0ID0gZnVuY3Rpb24gKGZpcnN0QXJnSW5kZXgsIG5vRHVwQ2hlY2spIHtcbiAgcmV0dXJuIFt0aGlzLnJ1bGVOYW1lXTtcbn07XG5cbnBleHBycy5Vbmljb2RlQ2hhci5wcm90b3R5cGUudG9Bcmd1bWVudE5hbWVMaXN0ID0gZnVuY3Rpb24gKGZpcnN0QXJnSW5kZXgsIG5vRHVwQ2hlY2spIHtcbiAgcmV0dXJuIFsnJCcgKyBmaXJzdEFyZ0luZGV4XTtcbn07XG5cbnBleHBycy5QYXJhbS5wcm90b3R5cGUudG9Bcmd1bWVudE5hbWVMaXN0ID0gZnVuY3Rpb24gKGZpcnN0QXJnSW5kZXgsIG5vRHVwQ2hlY2spIHtcbiAgcmV0dXJuIFsncGFyYW0nICsgdGhpcy5pbmRleF07XG59O1xuXG4vLyBcIlZhbHVlIHBleHByc1wiIChWYWx1ZSwgU3RyLCBBcnIsIE9iaikgYXJlIGdvaW5nIGF3YXkgc29vbiwgc28gd2UgZG9uJ3Qgd29ycnkgYWJvdXQgdGhlbSBoZXJlLlxuIiwiaW1wb3J0IHthYnN0cmFjdH0gZnJvbSAnLi9jb21tb24uanMnO1xuaW1wb3J0ICogYXMgcGV4cHJzIGZyb20gJy4vcGV4cHJzLW1haW4uanMnO1xuXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gT3BlcmF0aW9uc1xuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cblxuLy8gUmV0dXJucyBhIHN0cmluZyByZXByZXNlbnRpbmcgdGhlIFBFeHByLCBmb3IgdXNlIGFzIGEgVUkgbGFiZWwsIGV0Yy5cbnBleHBycy5QRXhwci5wcm90b3R5cGUudG9EaXNwbGF5U3RyaW5nID0gYWJzdHJhY3QoJ3RvRGlzcGxheVN0cmluZycpO1xuXG5wZXhwcnMuQWx0LnByb3RvdHlwZS50b0Rpc3BsYXlTdHJpbmcgPSBwZXhwcnMuU2VxLnByb3RvdHlwZS50b0Rpc3BsYXlTdHJpbmcgPSBmdW5jdGlvbiAoKSB7XG4gIGlmICh0aGlzLnNvdXJjZSkge1xuICAgIHJldHVybiB0aGlzLnNvdXJjZS50cmltbWVkKCkuY29udGVudHM7XG4gIH1cbiAgcmV0dXJuICdbJyArIHRoaXMuY29uc3RydWN0b3IubmFtZSArICddJztcbn07XG5cbnBleHBycy5hbnkudG9EaXNwbGF5U3RyaW5nID1cbiAgcGV4cHJzLmVuZC50b0Rpc3BsYXlTdHJpbmcgPVxuICBwZXhwcnMuSXRlci5wcm90b3R5cGUudG9EaXNwbGF5U3RyaW5nID1cbiAgcGV4cHJzLk5vdC5wcm90b3R5cGUudG9EaXNwbGF5U3RyaW5nID1cbiAgcGV4cHJzLkxvb2thaGVhZC5wcm90b3R5cGUudG9EaXNwbGF5U3RyaW5nID1cbiAgcGV4cHJzLkxleC5wcm90b3R5cGUudG9EaXNwbGF5U3RyaW5nID1cbiAgcGV4cHJzLlRlcm1pbmFsLnByb3RvdHlwZS50b0Rpc3BsYXlTdHJpbmcgPVxuICBwZXhwcnMuUmFuZ2UucHJvdG90eXBlLnRvRGlzcGxheVN0cmluZyA9XG4gIHBleHBycy5QYXJhbS5wcm90b3R5cGUudG9EaXNwbGF5U3RyaW5nID1cbiAgICBmdW5jdGlvbiAoKSB7XG4gICAgICByZXR1cm4gdGhpcy50b1N0cmluZygpO1xuICAgIH07XG5cbnBleHBycy5BcHBseS5wcm90b3R5cGUudG9EaXNwbGF5U3RyaW5nID0gZnVuY3Rpb24gKCkge1xuICBpZiAodGhpcy5hcmdzLmxlbmd0aCA+IDApIHtcbiAgICBjb25zdCBwcyA9IHRoaXMuYXJncy5tYXAoYXJnID0+IGFyZy50b0Rpc3BsYXlTdHJpbmcoKSk7XG4gICAgcmV0dXJuIHRoaXMucnVsZU5hbWUgKyAnPCcgKyBwcy5qb2luKCcsJykgKyAnPic7XG4gIH0gZWxzZSB7XG4gICAgcmV0dXJuIHRoaXMucnVsZU5hbWU7XG4gIH1cbn07XG5cbnBleHBycy5Vbmljb2RlQ2hhci5wcm90b3R5cGUudG9EaXNwbGF5U3RyaW5nID0gZnVuY3Rpb24gKCkge1xuICByZXR1cm4gJ1VuaWNvZGUgWycgKyB0aGlzLmNhdGVnb3J5T3JQcm9wICsgJ10gY2hhcmFjdGVyJztcbn07XG4iLCIvLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gUHJpdmF0ZSBzdHVmZlxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cblxuLypcbiAgYEZhaWx1cmVgcyByZXByZXNlbnQgZXhwcmVzc2lvbnMgdGhhdCB3ZXJlbid0IG1hdGNoZWQgd2hpbGUgcGFyc2luZy4gVGhleSBhcmUgdXNlZCB0byBnZW5lcmF0ZVxuICBlcnJvciBtZXNzYWdlcyBhdXRvbWF0aWNhbGx5LiBUaGUgaW50ZXJmYWNlIG9mIGBGYWlsdXJlYHMgaW5jbHVkZXMgdGhlIGNvbGxvd2luZyBtZXRob2RzOlxuXG4gIC0gZ2V0VGV4dCgpIDogU3RyaW5nXG4gIC0gZ2V0VHlwZSgpIDogU3RyaW5nICAob25lIG9mIHtcImRlc2NyaXB0aW9uXCIsIFwic3RyaW5nXCIsIFwiY29kZVwifSlcbiAgLSBpc0Rlc2NyaXB0aW9uKCkgOiBib29sXG4gIC0gaXNTdHJpbmdUZXJtaW5hbCgpIDogYm9vbFxuICAtIGlzQ29kZSgpIDogYm9vbFxuICAtIGlzRmx1ZmZ5KCkgOiBib29sXG4gIC0gbWFrZUZsdWZmeSgpIDogdm9pZFxuICAtIHN1YnN1bWVzKEZhaWx1cmUpIDogYm9vbFxuKi9cblxuZnVuY3Rpb24gaXNWYWxpZFR5cGUodHlwZSkge1xuICByZXR1cm4gdHlwZSA9PT0gJ2Rlc2NyaXB0aW9uJyB8fCB0eXBlID09PSAnc3RyaW5nJyB8fCB0eXBlID09PSAnY29kZSc7XG59XG5cbmV4cG9ydCBjbGFzcyBGYWlsdXJlIHtcbiAgY29uc3RydWN0b3IocGV4cHIsIHRleHQsIHR5cGUpIHtcbiAgICBpZiAoIWlzVmFsaWRUeXBlKHR5cGUpKSB7XG4gICAgICB0aHJvdyBuZXcgRXJyb3IoJ2ludmFsaWQgRmFpbHVyZSB0eXBlOiAnICsgdHlwZSk7XG4gICAgfVxuICAgIHRoaXMucGV4cHIgPSBwZXhwcjtcbiAgICB0aGlzLnRleHQgPSB0ZXh0O1xuICAgIHRoaXMudHlwZSA9IHR5cGU7XG4gICAgdGhpcy5mbHVmZnkgPSBmYWxzZTtcbiAgfVxuXG4gIGdldFBFeHByKCkge1xuICAgIHJldHVybiB0aGlzLnBleHByO1xuICB9XG5cbiAgZ2V0VGV4dCgpIHtcbiAgICByZXR1cm4gdGhpcy50ZXh0O1xuICB9XG5cbiAgZ2V0VHlwZSgpIHtcbiAgICByZXR1cm4gdGhpcy50eXBlO1xuICB9XG5cbiAgaXNEZXNjcmlwdGlvbigpIHtcbiAgICByZXR1cm4gdGhpcy50eXBlID09PSAnZGVzY3JpcHRpb24nO1xuICB9XG5cbiAgaXNTdHJpbmdUZXJtaW5hbCgpIHtcbiAgICByZXR1cm4gdGhpcy50eXBlID09PSAnc3RyaW5nJztcbiAgfVxuXG4gIGlzQ29kZSgpIHtcbiAgICByZXR1cm4gdGhpcy50eXBlID09PSAnY29kZSc7XG4gIH1cblxuICBpc0ZsdWZmeSgpIHtcbiAgICByZXR1cm4gdGhpcy5mbHVmZnk7XG4gIH1cblxuICBtYWtlRmx1ZmZ5KCkge1xuICAgIHRoaXMuZmx1ZmZ5ID0gdHJ1ZTtcbiAgfVxuXG4gIGNsZWFyRmx1ZmZ5KCkge1xuICAgIHRoaXMuZmx1ZmZ5ID0gZmFsc2U7XG4gIH1cblxuICBzdWJzdW1lcyh0aGF0KSB7XG4gICAgcmV0dXJuIChcbiAgICAgIHRoaXMuZ2V0VGV4dCgpID09PSB0aGF0LmdldFRleHQoKSAmJlxuICAgICAgdGhpcy50eXBlID09PSB0aGF0LnR5cGUgJiZcbiAgICAgICghdGhpcy5pc0ZsdWZmeSgpIHx8ICh0aGlzLmlzRmx1ZmZ5KCkgJiYgdGhhdC5pc0ZsdWZmeSgpKSlcbiAgICApO1xuICB9XG5cbiAgdG9TdHJpbmcoKSB7XG4gICAgcmV0dXJuIHRoaXMudHlwZSA9PT0gJ3N0cmluZycgPyBKU09OLnN0cmluZ2lmeSh0aGlzLmdldFRleHQoKSkgOiB0aGlzLmdldFRleHQoKTtcbiAgfVxuXG4gIGNsb25lKCkge1xuICAgIGNvbnN0IGZhaWx1cmUgPSBuZXcgRmFpbHVyZSh0aGlzLnBleHByLCB0aGlzLnRleHQsIHRoaXMudHlwZSk7XG4gICAgaWYgKHRoaXMuaXNGbHVmZnkoKSkge1xuICAgICAgZmFpbHVyZS5tYWtlRmx1ZmZ5KCk7XG4gICAgfVxuICAgIHJldHVybiBmYWlsdXJlO1xuICB9XG5cbiAgdG9LZXkoKSB7XG4gICAgcmV0dXJuIHRoaXMudG9TdHJpbmcoKSArICcjJyArIHRoaXMudHlwZTtcbiAgfVxufVxuIiwiaW1wb3J0IHthYnN0cmFjdH0gZnJvbSAnLi9jb21tb24uanMnO1xuaW1wb3J0ICogYXMgcGV4cHJzIGZyb20gJy4vcGV4cHJzLW1haW4uanMnO1xuaW1wb3J0IHtGYWlsdXJlfSBmcm9tICcuL0ZhaWx1cmUuanMnO1xuXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gT3BlcmF0aW9uc1xuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cblxucGV4cHJzLlBFeHByLnByb3RvdHlwZS50b0ZhaWx1cmUgPSBhYnN0cmFjdCgndG9GYWlsdXJlJyk7XG5cbnBleHBycy5hbnkudG9GYWlsdXJlID0gZnVuY3Rpb24gKGdyYW1tYXIpIHtcbiAgcmV0dXJuIG5ldyBGYWlsdXJlKHRoaXMsICdhbnkgb2JqZWN0JywgJ2Rlc2NyaXB0aW9uJyk7XG59O1xuXG5wZXhwcnMuZW5kLnRvRmFpbHVyZSA9IGZ1bmN0aW9uIChncmFtbWFyKSB7XG4gIHJldHVybiBuZXcgRmFpbHVyZSh0aGlzLCAnZW5kIG9mIGlucHV0JywgJ2Rlc2NyaXB0aW9uJyk7XG59O1xuXG5wZXhwcnMuVGVybWluYWwucHJvdG90eXBlLnRvRmFpbHVyZSA9IGZ1bmN0aW9uIChncmFtbWFyKSB7XG4gIHJldHVybiBuZXcgRmFpbHVyZSh0aGlzLCB0aGlzLm9iaiwgJ3N0cmluZycpO1xufTtcblxucGV4cHJzLlJhbmdlLnByb3RvdHlwZS50b0ZhaWx1cmUgPSBmdW5jdGlvbiAoZ3JhbW1hcikge1xuICAvLyBUT0RPOiBjb21lIHVwIHdpdGggc29tZXRoaW5nIGJldHRlclxuICByZXR1cm4gbmV3IEZhaWx1cmUodGhpcywgSlNPTi5zdHJpbmdpZnkodGhpcy5mcm9tKSArICcuLicgKyBKU09OLnN0cmluZ2lmeSh0aGlzLnRvKSwgJ2NvZGUnKTtcbn07XG5cbnBleHBycy5Ob3QucHJvdG90eXBlLnRvRmFpbHVyZSA9IGZ1bmN0aW9uIChncmFtbWFyKSB7XG4gIGNvbnN0IGRlc2NyaXB0aW9uID1cbiAgICB0aGlzLmV4cHIgPT09IHBleHBycy5hbnkgPyAnbm90aGluZycgOiAnbm90ICcgKyB0aGlzLmV4cHIudG9GYWlsdXJlKGdyYW1tYXIpO1xuICByZXR1cm4gbmV3IEZhaWx1cmUodGhpcywgZGVzY3JpcHRpb24sICdkZXNjcmlwdGlvbicpO1xufTtcblxucGV4cHJzLkxvb2thaGVhZC5wcm90b3R5cGUudG9GYWlsdXJlID0gZnVuY3Rpb24gKGdyYW1tYXIpIHtcbiAgcmV0dXJuIHRoaXMuZXhwci50b0ZhaWx1cmUoZ3JhbW1hcik7XG59O1xuXG5wZXhwcnMuQXBwbHkucHJvdG90eXBlLnRvRmFpbHVyZSA9IGZ1bmN0aW9uIChncmFtbWFyKSB7XG4gIGxldCB7ZGVzY3JpcHRpb259ID0gZ3JhbW1hci5ydWxlc1t0aGlzLnJ1bGVOYW1lXTtcbiAgaWYgKCFkZXNjcmlwdGlvbikge1xuICAgIGNvbnN0IGFydGljbGUgPSAvXlthZWlvdUFFSU9VXS8udGVzdCh0aGlzLnJ1bGVOYW1lKSA/ICdhbicgOiAnYSc7XG4gICAgZGVzY3JpcHRpb24gPSBhcnRpY2xlICsgJyAnICsgdGhpcy5ydWxlTmFtZTtcbiAgfVxuICByZXR1cm4gbmV3IEZhaWx1cmUodGhpcywgZGVzY3JpcHRpb24sICdkZXNjcmlwdGlvbicpO1xufTtcblxucGV4cHJzLlVuaWNvZGVDaGFyLnByb3RvdHlwZS50b0ZhaWx1cmUgPSBmdW5jdGlvbiAoZ3JhbW1hcikge1xuICByZXR1cm4gbmV3IEZhaWx1cmUodGhpcywgJ2EgVW5pY29kZSBbJyArIHRoaXMuY2F0ZWdvcnlPclByb3AgKyAnXSBjaGFyYWN0ZXInLCAnZGVzY3JpcHRpb24nKTtcbn07XG5cbnBleHBycy5BbHQucHJvdG90eXBlLnRvRmFpbHVyZSA9IGZ1bmN0aW9uIChncmFtbWFyKSB7XG4gIGNvbnN0IGZzID0gdGhpcy50ZXJtcy5tYXAodCA9PiB0LnRvRmFpbHVyZShncmFtbWFyKSk7XG4gIGNvbnN0IGRlc2NyaXB0aW9uID0gJygnICsgZnMuam9pbignIG9yICcpICsgJyknO1xuICByZXR1cm4gbmV3IEZhaWx1cmUodGhpcywgZGVzY3JpcHRpb24sICdkZXNjcmlwdGlvbicpO1xufTtcblxucGV4cHJzLlNlcS5wcm90b3R5cGUudG9GYWlsdXJlID0gZnVuY3Rpb24gKGdyYW1tYXIpIHtcbiAgY29uc3QgZnMgPSB0aGlzLmZhY3RvcnMubWFwKGYgPT4gZi50b0ZhaWx1cmUoZ3JhbW1hcikpO1xuICBjb25zdCBkZXNjcmlwdGlvbiA9ICcoJyArIGZzLmpvaW4oJyAnKSArICcpJztcbiAgcmV0dXJuIG5ldyBGYWlsdXJlKHRoaXMsIGRlc2NyaXB0aW9uLCAnZGVzY3JpcHRpb24nKTtcbn07XG5cbnBleHBycy5JdGVyLnByb3RvdHlwZS50b0ZhaWx1cmUgPSBmdW5jdGlvbiAoZ3JhbW1hcikge1xuICBjb25zdCBkZXNjcmlwdGlvbiA9ICcoJyArIHRoaXMuZXhwci50b0ZhaWx1cmUoZ3JhbW1hcikgKyB0aGlzLm9wZXJhdG9yICsgJyknO1xuICByZXR1cm4gbmV3IEZhaWx1cmUodGhpcywgZGVzY3JpcHRpb24sICdkZXNjcmlwdGlvbicpO1xufTtcbiIsImltcG9ydCB7YWJzdHJhY3R9IGZyb20gJy4vY29tbW9uLmpzJztcbmltcG9ydCAqIGFzIHBleHBycyBmcm9tICcuL3BleHBycy1tYWluLmpzJztcblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cbi8vIE9wZXJhdGlvbnNcbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG5cbi8qXG4gIGUxLnRvU3RyaW5nKCkgPT09IGUyLnRvU3RyaW5nKCkgPT0+IGUxIGFuZCBlMiBhcmUgc2VtYW50aWNhbGx5IGVxdWl2YWxlbnQuXG4gIE5vdGUgdGhhdCB0aGlzIGlzIG5vdCBhbiBpZmYgKDw9PT4pOiBlLmcuLFxuICAoflwiYlwiIFwiYVwiKS50b1N0cmluZygpICE9PSAoXCJhXCIpLnRvU3RyaW5nKCksIGV2ZW4gdGhvdWdoXG4gIH5cImJcIiBcImFcIiBhbmQgXCJhXCIgYXJlIGludGVyY2hhbmdlYWJsZSBpbiBhbnkgZ3JhbW1hcixcbiAgYm90aCBpbiB0ZXJtcyBvZiB0aGUgbGFuZ3VhZ2VzIHRoZXkgYWNjZXB0IGFuZCB0aGVpciBhcml0aWVzLlxuKi9cbnBleHBycy5QRXhwci5wcm90b3R5cGUudG9TdHJpbmcgPSBhYnN0cmFjdCgndG9TdHJpbmcnKTtcblxucGV4cHJzLmFueS50b1N0cmluZyA9IGZ1bmN0aW9uICgpIHtcbiAgcmV0dXJuICdhbnknO1xufTtcblxucGV4cHJzLmVuZC50b1N0cmluZyA9IGZ1bmN0aW9uICgpIHtcbiAgcmV0dXJuICdlbmQnO1xufTtcblxucGV4cHJzLlRlcm1pbmFsLnByb3RvdHlwZS50b1N0cmluZyA9IGZ1bmN0aW9uICgpIHtcbiAgcmV0dXJuIEpTT04uc3RyaW5naWZ5KHRoaXMub2JqKTtcbn07XG5cbnBleHBycy5SYW5nZS5wcm90b3R5cGUudG9TdHJpbmcgPSBmdW5jdGlvbiAoKSB7XG4gIHJldHVybiBKU09OLnN0cmluZ2lmeSh0aGlzLmZyb20pICsgJy4uJyArIEpTT04uc3RyaW5naWZ5KHRoaXMudG8pO1xufTtcblxucGV4cHJzLlBhcmFtLnByb3RvdHlwZS50b1N0cmluZyA9IGZ1bmN0aW9uICgpIHtcbiAgcmV0dXJuICckJyArIHRoaXMuaW5kZXg7XG59O1xuXG5wZXhwcnMuTGV4LnByb3RvdHlwZS50b1N0cmluZyA9IGZ1bmN0aW9uICgpIHtcbiAgcmV0dXJuICcjKCcgKyB0aGlzLmV4cHIudG9TdHJpbmcoKSArICcpJztcbn07XG5cbnBleHBycy5BbHQucHJvdG90eXBlLnRvU3RyaW5nID0gZnVuY3Rpb24gKCkge1xuICByZXR1cm4gdGhpcy50ZXJtcy5sZW5ndGggPT09IDFcbiAgICA/IHRoaXMudGVybXNbMF0udG9TdHJpbmcoKVxuICAgIDogJygnICsgdGhpcy50ZXJtcy5tYXAodGVybSA9PiB0ZXJtLnRvU3RyaW5nKCkpLmpvaW4oJyB8ICcpICsgJyknO1xufTtcblxucGV4cHJzLlNlcS5wcm90b3R5cGUudG9TdHJpbmcgPSBmdW5jdGlvbiAoKSB7XG4gIHJldHVybiB0aGlzLmZhY3RvcnMubGVuZ3RoID09PSAxXG4gICAgPyB0aGlzLmZhY3RvcnNbMF0udG9TdHJpbmcoKVxuICAgIDogJygnICsgdGhpcy5mYWN0b3JzLm1hcChmYWN0b3IgPT4gZmFjdG9yLnRvU3RyaW5nKCkpLmpvaW4oJyAnKSArICcpJztcbn07XG5cbnBleHBycy5JdGVyLnByb3RvdHlwZS50b1N0cmluZyA9IGZ1bmN0aW9uICgpIHtcbiAgcmV0dXJuIHRoaXMuZXhwciArIHRoaXMub3BlcmF0b3I7XG59O1xuXG5wZXhwcnMuTm90LnByb3RvdHlwZS50b1N0cmluZyA9IGZ1bmN0aW9uICgpIHtcbiAgcmV0dXJuICd+JyArIHRoaXMuZXhwcjtcbn07XG5cbnBleHBycy5Mb29rYWhlYWQucHJvdG90eXBlLnRvU3RyaW5nID0gZnVuY3Rpb24gKCkge1xuICByZXR1cm4gJyYnICsgdGhpcy5leHByO1xufTtcblxucGV4cHJzLkFwcGx5LnByb3RvdHlwZS50b1N0cmluZyA9IGZ1bmN0aW9uICgpIHtcbiAgaWYgKHRoaXMuYXJncy5sZW5ndGggPiAwKSB7XG4gICAgY29uc3QgcHMgPSB0aGlzLmFyZ3MubWFwKGFyZyA9PiBhcmcudG9TdHJpbmcoKSk7XG4gICAgcmV0dXJuIHRoaXMucnVsZU5hbWUgKyAnPCcgKyBwcy5qb2luKCcsJykgKyAnPic7XG4gIH0gZWxzZSB7XG4gICAgcmV0dXJuIHRoaXMucnVsZU5hbWU7XG4gIH1cbn07XG5cbnBleHBycy5Vbmljb2RlQ2hhci5wcm90b3R5cGUudG9TdHJpbmcgPSBmdW5jdGlvbiAoKSB7XG4gIHJldHVybiAnXFxcXHB7JyArIHRoaXMuY2F0ZWdvcnlPclByb3AgKyAnfSc7XG59O1xuIiwiaW1wb3J0IHtGYWlsdXJlfSBmcm9tICcuL0ZhaWx1cmUuanMnO1xuaW1wb3J0IHtUZXJtaW5hbE5vZGV9IGZyb20gJy4vbm9kZXMuanMnO1xuaW1wb3J0IHthc3NlcnR9IGZyb20gJy4vY29tbW9uLmpzJztcbmltcG9ydCB7UEV4cHIsIFRlcm1pbmFsfSBmcm9tICcuL3BleHBycy1tYWluLmpzJztcblxuZXhwb3J0IGNsYXNzIENhc2VJbnNlbnNpdGl2ZVRlcm1pbmFsIGV4dGVuZHMgUEV4cHIge1xuICBjb25zdHJ1Y3RvcihwYXJhbSkge1xuICAgIHN1cGVyKCk7XG4gICAgdGhpcy5vYmogPSBwYXJhbTtcbiAgfVxuXG4gIF9nZXRTdHJpbmcoc3RhdGUpIHtcbiAgICBjb25zdCB0ZXJtaW5hbCA9IHN0YXRlLmN1cnJlbnRBcHBsaWNhdGlvbigpLmFyZ3NbdGhpcy5vYmouaW5kZXhdO1xuICAgIGFzc2VydCh0ZXJtaW5hbCBpbnN0YW5jZW9mIFRlcm1pbmFsLCAnZXhwZWN0ZWQgYSBUZXJtaW5hbCBleHByZXNzaW9uJyk7XG4gICAgcmV0dXJuIHRlcm1pbmFsLm9iajtcbiAgfVxuXG4gIC8vIEltcGxlbWVudGF0aW9uIG9mIHRoZSBQRXhwciBBUElcblxuICBhbGxvd3NTa2lwcGluZ1ByZWNlZGluZ1NwYWNlKCkge1xuICAgIHJldHVybiB0cnVlO1xuICB9XG5cbiAgZXZhbChzdGF0ZSkge1xuICAgIGNvbnN0IHtpbnB1dFN0cmVhbX0gPSBzdGF0ZTtcbiAgICBjb25zdCBvcmlnUG9zID0gaW5wdXRTdHJlYW0ucG9zO1xuICAgIGNvbnN0IG1hdGNoU3RyID0gdGhpcy5fZ2V0U3RyaW5nKHN0YXRlKTtcbiAgICBpZiAoIWlucHV0U3RyZWFtLm1hdGNoU3RyaW5nKG1hdGNoU3RyLCB0cnVlKSkge1xuICAgICAgc3RhdGUucHJvY2Vzc0ZhaWx1cmUob3JpZ1BvcywgdGhpcyk7XG4gICAgICByZXR1cm4gZmFsc2U7XG4gICAgfSBlbHNlIHtcbiAgICAgIHN0YXRlLnB1c2hCaW5kaW5nKG5ldyBUZXJtaW5hbE5vZGUobWF0Y2hTdHIubGVuZ3RoKSwgb3JpZ1Bvcyk7XG4gICAgICByZXR1cm4gdHJ1ZTtcbiAgICB9XG4gIH1cblxuICBnZXRBcml0eSgpIHtcbiAgICByZXR1cm4gMTtcbiAgfVxuXG4gIHN1YnN0aXR1dGVQYXJhbXMoYWN0dWFscykge1xuICAgIHJldHVybiBuZXcgQ2FzZUluc2Vuc2l0aXZlVGVybWluYWwodGhpcy5vYmouc3Vic3RpdHV0ZVBhcmFtcyhhY3R1YWxzKSk7XG4gIH1cblxuICB0b0Rpc3BsYXlTdHJpbmcoKSB7XG4gICAgcmV0dXJuIHRoaXMub2JqLnRvRGlzcGxheVN0cmluZygpICsgJyAoY2FzZS1pbnNlbnNpdGl2ZSknO1xuICB9XG5cbiAgdG9GYWlsdXJlKGdyYW1tYXIpIHtcbiAgICByZXR1cm4gbmV3IEZhaWx1cmUoXG4gICAgICB0aGlzLFxuICAgICAgdGhpcy5vYmoudG9GYWlsdXJlKGdyYW1tYXIpICsgJyAoY2FzZS1pbnNlbnNpdGl2ZSknLFxuICAgICAgJ2Rlc2NyaXB0aW9uJ1xuICAgICk7XG4gIH1cblxuICBfaXNOdWxsYWJsZShncmFtbWFyLCBtZW1vKSB7XG4gICAgcmV0dXJuIHRoaXMub2JqLl9pc051bGxhYmxlKGdyYW1tYXIsIG1lbW8pO1xuICB9XG59XG4iLCIvLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gRXh0ZW5zaW9uc1xuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cblxuaW1wb3J0ICcuL3BleHBycy1hbGxvd3NTa2lwcGluZ1ByZWNlZGluZ1NwYWNlLmpzJztcbmltcG9ydCAnLi9wZXhwcnMtYXNzZXJ0QWxsQXBwbGljYXRpb25zQXJlVmFsaWQuanMnO1xuaW1wb3J0ICcuL3BleHBycy1hc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eS5qcyc7XG5pbXBvcnQgJy4vcGV4cHJzLWFzc2VydEl0ZXJhdGVkRXhwcnNBcmVOb3ROdWxsYWJsZS5qcyc7XG5pbXBvcnQgJy4vcGV4cHJzLWV2YWwuanMnO1xuaW1wb3J0ICcuL3BleHBycy1nZXRBcml0eS5qcyc7XG5pbXBvcnQgJy4vcGV4cHJzLW91dHB1dFJlY2lwZS5qcyc7XG5pbXBvcnQgJy4vcGV4cHJzLWludHJvZHVjZVBhcmFtcy5qcyc7XG5pbXBvcnQgJy4vcGV4cHJzLWlzTnVsbGFibGUuanMnO1xuaW1wb3J0ICcuL3BleHBycy1zdWJzdGl0dXRlUGFyYW1zLmpzJztcbmltcG9ydCAnLi9wZXhwcnMtdG9Bcmd1bWVudE5hbWVMaXN0LmpzJztcbmltcG9ydCAnLi9wZXhwcnMtdG9EaXNwbGF5U3RyaW5nLmpzJztcbmltcG9ydCAnLi9wZXhwcnMtdG9GYWlsdXJlLmpzJztcbmltcG9ydCAnLi9wZXhwcnMtdG9TdHJpbmcuanMnO1xuXG5leHBvcnQgKiBmcm9tICcuL3BleHBycy1tYWluLmpzJztcbmV4cG9ydCB7Q2FzZUluc2Vuc2l0aXZlVGVybWluYWx9IGZyb20gJy4vQ2FzZUluc2Vuc2l0aXZlVGVybWluYWwuanMnO1xuIiwiaW1wb3J0IHtJbnB1dFN0cmVhbX0gZnJvbSAnLi9JbnB1dFN0cmVhbS5qcyc7XG5pbXBvcnQge01hdGNoUmVzdWx0fSBmcm9tICcuL01hdGNoUmVzdWx0LmpzJztcbmltcG9ydCB7UG9zSW5mb30gZnJvbSAnLi9Qb3NJbmZvLmpzJztcbmltcG9ydCB7VHJhY2V9IGZyb20gJy4vVHJhY2UuanMnO1xuaW1wb3J0ICogYXMgcGV4cHJzIGZyb20gJy4vcGV4cHJzLmpzJztcbmltcG9ydCAqIGFzIHV0aWwgZnJvbSAnLi91dGlsLmpzJztcblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cbi8vIFByaXZhdGUgc3R1ZmZcbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG5cbmxldCBidWlsdEluQXBwbHlTeW50YWN0aWNCb2R5O1xuXG51dGlsLmF3YWl0QnVpbHRJblJ1bGVzKGJ1aWx0SW5SdWxlcyA9PiB7XG4gIGJ1aWx0SW5BcHBseVN5bnRhY3RpY0JvZHkgPSBidWlsdEluUnVsZXMucnVsZXMuYXBwbHlTeW50YWN0aWMuYm9keTtcbn0pO1xuXG5jb25zdCBhcHBseVNwYWNlcyA9IG5ldyBwZXhwcnMuQXBwbHkoJ3NwYWNlcycpO1xuXG5leHBvcnQgY2xhc3MgTWF0Y2hTdGF0ZSB7XG4gIGNvbnN0cnVjdG9yKG1hdGNoZXIsIHN0YXJ0RXhwciwgb3B0UG9zaXRpb25Ub1JlY29yZEZhaWx1cmVzKSB7XG4gICAgdGhpcy5tYXRjaGVyID0gbWF0Y2hlcjtcbiAgICB0aGlzLnN0YXJ0RXhwciA9IHN0YXJ0RXhwcjtcblxuICAgIHRoaXMuZ3JhbW1hciA9IG1hdGNoZXIuZ3JhbW1hcjtcbiAgICB0aGlzLmlucHV0ID0gbWF0Y2hlci5nZXRJbnB1dCgpO1xuICAgIHRoaXMuaW5wdXRTdHJlYW0gPSBuZXcgSW5wdXRTdHJlYW0odGhpcy5pbnB1dCk7XG4gICAgdGhpcy5tZW1vVGFibGUgPSBtYXRjaGVyLl9tZW1vVGFibGU7XG5cbiAgICB0aGlzLnVzZXJEYXRhID0gdW5kZWZpbmVkO1xuICAgIHRoaXMuZG9Ob3RNZW1vaXplID0gZmFsc2U7XG5cbiAgICB0aGlzLl9iaW5kaW5ncyA9IFtdO1xuICAgIHRoaXMuX2JpbmRpbmdPZmZzZXRzID0gW107XG4gICAgdGhpcy5fYXBwbGljYXRpb25TdGFjayA9IFtdO1xuICAgIHRoaXMuX3Bvc1N0YWNrID0gWzBdO1xuICAgIHRoaXMuaW5MZXhpZmllZENvbnRleHRTdGFjayA9IFtmYWxzZV07XG5cbiAgICB0aGlzLnJpZ2h0bW9zdEZhaWx1cmVQb3NpdGlvbiA9IC0xO1xuICAgIHRoaXMuX3JpZ2h0bW9zdEZhaWx1cmVQb3NpdGlvblN0YWNrID0gW107XG4gICAgdGhpcy5fcmVjb3JkZWRGYWlsdXJlc1N0YWNrID0gW107XG5cbiAgICBpZiAob3B0UG9zaXRpb25Ub1JlY29yZEZhaWx1cmVzICE9PSB1bmRlZmluZWQpIHtcbiAgICAgIHRoaXMucG9zaXRpb25Ub1JlY29yZEZhaWx1cmVzID0gb3B0UG9zaXRpb25Ub1JlY29yZEZhaWx1cmVzO1xuICAgICAgdGhpcy5yZWNvcmRlZEZhaWx1cmVzID0gT2JqZWN0LmNyZWF0ZShudWxsKTtcbiAgICB9XG4gIH1cblxuICBwb3NUb09mZnNldChwb3MpIHtcbiAgICByZXR1cm4gcG9zIC0gdGhpcy5fcG9zU3RhY2tbdGhpcy5fcG9zU3RhY2subGVuZ3RoIC0gMV07XG4gIH1cblxuICBlbnRlckFwcGxpY2F0aW9uKHBvc0luZm8sIGFwcCkge1xuICAgIHRoaXMuX3Bvc1N0YWNrLnB1c2godGhpcy5pbnB1dFN0cmVhbS5wb3MpO1xuICAgIHRoaXMuX2FwcGxpY2F0aW9uU3RhY2sucHVzaChhcHApO1xuICAgIHRoaXMuaW5MZXhpZmllZENvbnRleHRTdGFjay5wdXNoKGZhbHNlKTtcbiAgICBwb3NJbmZvLmVudGVyKGFwcCk7XG4gICAgdGhpcy5fcmlnaHRtb3N0RmFpbHVyZVBvc2l0aW9uU3RhY2sucHVzaCh0aGlzLnJpZ2h0bW9zdEZhaWx1cmVQb3NpdGlvbik7XG4gICAgdGhpcy5yaWdodG1vc3RGYWlsdXJlUG9zaXRpb24gPSAtMTtcbiAgfVxuXG4gIGV4aXRBcHBsaWNhdGlvbihwb3NJbmZvLCBvcHROb2RlKSB7XG4gICAgY29uc3Qgb3JpZ1BvcyA9IHRoaXMuX3Bvc1N0YWNrLnBvcCgpO1xuICAgIHRoaXMuX2FwcGxpY2F0aW9uU3RhY2sucG9wKCk7XG4gICAgdGhpcy5pbkxleGlmaWVkQ29udGV4dFN0YWNrLnBvcCgpO1xuICAgIHBvc0luZm8uZXhpdCgpO1xuXG4gICAgdGhpcy5yaWdodG1vc3RGYWlsdXJlUG9zaXRpb24gPSBNYXRoLm1heChcbiAgICAgIHRoaXMucmlnaHRtb3N0RmFpbHVyZVBvc2l0aW9uLFxuICAgICAgdGhpcy5fcmlnaHRtb3N0RmFpbHVyZVBvc2l0aW9uU3RhY2sucG9wKClcbiAgICApO1xuXG4gICAgaWYgKG9wdE5vZGUpIHtcbiAgICAgIHRoaXMucHVzaEJpbmRpbmcob3B0Tm9kZSwgb3JpZ1Bvcyk7XG4gICAgfVxuICB9XG5cbiAgZW50ZXJMZXhpZmllZENvbnRleHQoKSB7XG4gICAgdGhpcy5pbkxleGlmaWVkQ29udGV4dFN0YWNrLnB1c2godHJ1ZSk7XG4gIH1cblxuICBleGl0TGV4aWZpZWRDb250ZXh0KCkge1xuICAgIHRoaXMuaW5MZXhpZmllZENvbnRleHRTdGFjay5wb3AoKTtcbiAgfVxuXG4gIGN1cnJlbnRBcHBsaWNhdGlvbigpIHtcbiAgICByZXR1cm4gdGhpcy5fYXBwbGljYXRpb25TdGFja1t0aGlzLl9hcHBsaWNhdGlvblN0YWNrLmxlbmd0aCAtIDFdO1xuICB9XG5cbiAgaW5TeW50YWN0aWNDb250ZXh0KCkge1xuICAgIGNvbnN0IGN1cnJlbnRBcHBsaWNhdGlvbiA9IHRoaXMuY3VycmVudEFwcGxpY2F0aW9uKCk7XG4gICAgaWYgKGN1cnJlbnRBcHBsaWNhdGlvbikge1xuICAgICAgcmV0dXJuIGN1cnJlbnRBcHBsaWNhdGlvbi5pc1N5bnRhY3RpYygpICYmICF0aGlzLmluTGV4aWZpZWRDb250ZXh0KCk7XG4gICAgfSBlbHNlIHtcbiAgICAgIC8vIFRoZSB0b3AtbGV2ZWwgY29udGV4dCBpcyBzeW50YWN0aWMgaWYgdGhlIHN0YXJ0IGFwcGxpY2F0aW9uIGlzLlxuICAgICAgcmV0dXJuIHRoaXMuc3RhcnRFeHByLmZhY3RvcnNbMF0uaXNTeW50YWN0aWMoKTtcbiAgICB9XG4gIH1cblxuICBpbkxleGlmaWVkQ29udGV4dCgpIHtcbiAgICByZXR1cm4gdGhpcy5pbkxleGlmaWVkQ29udGV4dFN0YWNrW3RoaXMuaW5MZXhpZmllZENvbnRleHRTdGFjay5sZW5ndGggLSAxXTtcbiAgfVxuXG4gIHNraXBTcGFjZXMoKSB7XG4gICAgdGhpcy5wdXNoRmFpbHVyZXNJbmZvKCk7XG4gICAgdGhpcy5ldmFsKGFwcGx5U3BhY2VzKTtcbiAgICB0aGlzLnBvcEJpbmRpbmcoKTtcbiAgICB0aGlzLnBvcEZhaWx1cmVzSW5mbygpO1xuICAgIHJldHVybiB0aGlzLmlucHV0U3RyZWFtLnBvcztcbiAgfVxuXG4gIHNraXBTcGFjZXNJZkluU3ludGFjdGljQ29udGV4dCgpIHtcbiAgICByZXR1cm4gdGhpcy5pblN5bnRhY3RpY0NvbnRleHQoKSA/IHRoaXMuc2tpcFNwYWNlcygpIDogdGhpcy5pbnB1dFN0cmVhbS5wb3M7XG4gIH1cblxuICBtYXliZVNraXBTcGFjZXNCZWZvcmUoZXhwcikge1xuICAgIGlmIChleHByLmFsbG93c1NraXBwaW5nUHJlY2VkaW5nU3BhY2UoKSAmJiBleHByICE9PSBhcHBseVNwYWNlcykge1xuICAgICAgcmV0dXJuIHRoaXMuc2tpcFNwYWNlc0lmSW5TeW50YWN0aWNDb250ZXh0KCk7XG4gICAgfSBlbHNlIHtcbiAgICAgIHJldHVybiB0aGlzLmlucHV0U3RyZWFtLnBvcztcbiAgICB9XG4gIH1cblxuICBwdXNoQmluZGluZyhub2RlLCBvcmlnUG9zKSB7XG4gICAgdGhpcy5fYmluZGluZ3MucHVzaChub2RlKTtcbiAgICB0aGlzLl9iaW5kaW5nT2Zmc2V0cy5wdXNoKHRoaXMucG9zVG9PZmZzZXQob3JpZ1BvcykpO1xuICB9XG5cbiAgcG9wQmluZGluZygpIHtcbiAgICB0aGlzLl9iaW5kaW5ncy5wb3AoKTtcbiAgICB0aGlzLl9iaW5kaW5nT2Zmc2V0cy5wb3AoKTtcbiAgfVxuXG4gIG51bUJpbmRpbmdzKCkge1xuICAgIHJldHVybiB0aGlzLl9iaW5kaW5ncy5sZW5ndGg7XG4gIH1cblxuICB0cnVuY2F0ZUJpbmRpbmdzKG5ld0xlbmd0aCkge1xuICAgIC8vIFllcywgdGhpcyBpcyB0aGlzIHJlYWxseSBmYXN0ZXIgdGhhbiBzZXR0aW5nIHRoZSBgbGVuZ3RoYCBwcm9wZXJ0eSAodGVzdGVkIHdpdGhcbiAgICAvLyBiaW4vZXM1YmVuY2ggb24gTm9kZSB2Ni4xLjApLlxuICAgIC8vIFVwZGF0ZSAyMDIxLTEwLTI1OiBzdGlsbCB0cnVlIG9uIHYxNC4xNS41IOKAlCBpdCdzIH4yMCUgc3BlZWR1cCBvbiBlczViZW5jaC5cbiAgICB3aGlsZSAodGhpcy5fYmluZGluZ3MubGVuZ3RoID4gbmV3TGVuZ3RoKSB7XG4gICAgICB0aGlzLnBvcEJpbmRpbmcoKTtcbiAgICB9XG4gIH1cblxuICBnZXRDdXJyZW50UG9zSW5mbygpIHtcbiAgICByZXR1cm4gdGhpcy5nZXRQb3NJbmZvKHRoaXMuaW5wdXRTdHJlYW0ucG9zKTtcbiAgfVxuXG4gIGdldFBvc0luZm8ocG9zKSB7XG4gICAgbGV0IHBvc0luZm8gPSB0aGlzLm1lbW9UYWJsZVtwb3NdO1xuICAgIGlmICghcG9zSW5mbykge1xuICAgICAgcG9zSW5mbyA9IHRoaXMubWVtb1RhYmxlW3Bvc10gPSBuZXcgUG9zSW5mbygpO1xuICAgIH1cbiAgICByZXR1cm4gcG9zSW5mbztcbiAgfVxuXG4gIHByb2Nlc3NGYWlsdXJlKHBvcywgZXhwcikge1xuICAgIHRoaXMucmlnaHRtb3N0RmFpbHVyZVBvc2l0aW9uID0gTWF0aC5tYXgodGhpcy5yaWdodG1vc3RGYWlsdXJlUG9zaXRpb24sIHBvcyk7XG5cbiAgICBpZiAodGhpcy5yZWNvcmRlZEZhaWx1cmVzICYmIHBvcyA9PT0gdGhpcy5wb3NpdGlvblRvUmVjb3JkRmFpbHVyZXMpIHtcbiAgICAgIGNvbnN0IGFwcCA9IHRoaXMuY3VycmVudEFwcGxpY2F0aW9uKCk7XG4gICAgICBpZiAoYXBwKSB7XG4gICAgICAgIC8vIFN1YnN0aXR1dGUgcGFyYW1ldGVycyB3aXRoIHRoZSBhY3R1YWwgcGV4cHJzIHRoYXQgd2VyZSBwYXNzZWQgdG9cbiAgICAgICAgLy8gdGhlIGN1cnJlbnQgcnVsZS5cbiAgICAgICAgZXhwciA9IGV4cHIuc3Vic3RpdHV0ZVBhcmFtcyhhcHAuYXJncyk7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICAvLyBUaGlzIGJyYW5jaCBpcyBvbmx5IHJlYWNoZWQgZm9yIHRoZSBcImVuZC1jaGVja1wiIHRoYXQgaXNcbiAgICAgICAgLy8gcGVyZm9ybWVkIGFmdGVyIHRoZSB0b3AtbGV2ZWwgYXBwbGljYXRpb24uIEluIHRoYXQgY2FzZSxcbiAgICAgICAgLy8gZXhwciA9PT0gcGV4cHJzLmVuZCBzbyB0aGVyZSBpcyBubyBuZWVkIHRvIHN1YnN0aXR1dGVcbiAgICAgICAgLy8gcGFyYW1ldGVycy5cbiAgICAgIH1cblxuICAgICAgdGhpcy5yZWNvcmRGYWlsdXJlKGV4cHIudG9GYWlsdXJlKHRoaXMuZ3JhbW1hciksIGZhbHNlKTtcbiAgICB9XG4gIH1cblxuICByZWNvcmRGYWlsdXJlKGZhaWx1cmUsIHNob3VsZENsb25lSWZOZXcpIHtcbiAgICBjb25zdCBrZXkgPSBmYWlsdXJlLnRvS2V5KCk7XG4gICAgaWYgKCF0aGlzLnJlY29yZGVkRmFpbHVyZXNba2V5XSkge1xuICAgICAgdGhpcy5yZWNvcmRlZEZhaWx1cmVzW2tleV0gPSBzaG91bGRDbG9uZUlmTmV3ID8gZmFpbHVyZS5jbG9uZSgpIDogZmFpbHVyZTtcbiAgICB9IGVsc2UgaWYgKHRoaXMucmVjb3JkZWRGYWlsdXJlc1trZXldLmlzRmx1ZmZ5KCkgJiYgIWZhaWx1cmUuaXNGbHVmZnkoKSkge1xuICAgICAgdGhpcy5yZWNvcmRlZEZhaWx1cmVzW2tleV0uY2xlYXJGbHVmZnkoKTtcbiAgICB9XG4gIH1cblxuICByZWNvcmRGYWlsdXJlcyhmYWlsdXJlcywgc2hvdWxkQ2xvbmVJZk5ldykge1xuICAgIE9iamVjdC5rZXlzKGZhaWx1cmVzKS5mb3JFYWNoKGtleSA9PiB7XG4gICAgICB0aGlzLnJlY29yZEZhaWx1cmUoZmFpbHVyZXNba2V5XSwgc2hvdWxkQ2xvbmVJZk5ldyk7XG4gICAgfSk7XG4gIH1cblxuICBjbG9uZVJlY29yZGVkRmFpbHVyZXMoKSB7XG4gICAgaWYgKCF0aGlzLnJlY29yZGVkRmFpbHVyZXMpIHtcbiAgICAgIHJldHVybiB1bmRlZmluZWQ7XG4gICAgfVxuXG4gICAgY29uc3QgYW5zID0gT2JqZWN0LmNyZWF0ZShudWxsKTtcbiAgICBPYmplY3Qua2V5cyh0aGlzLnJlY29yZGVkRmFpbHVyZXMpLmZvckVhY2goa2V5ID0+IHtcbiAgICAgIGFuc1trZXldID0gdGhpcy5yZWNvcmRlZEZhaWx1cmVzW2tleV0uY2xvbmUoKTtcbiAgICB9KTtcbiAgICByZXR1cm4gYW5zO1xuICB9XG5cbiAgZ2V0UmlnaHRtb3N0RmFpbHVyZVBvc2l0aW9uKCkge1xuICAgIHJldHVybiB0aGlzLnJpZ2h0bW9zdEZhaWx1cmVQb3NpdGlvbjtcbiAgfVxuXG4gIF9nZXRSaWdodG1vc3RGYWlsdXJlT2Zmc2V0KCkge1xuICAgIHJldHVybiB0aGlzLnJpZ2h0bW9zdEZhaWx1cmVQb3NpdGlvbiA+PSAwXG4gICAgICA/IHRoaXMucG9zVG9PZmZzZXQodGhpcy5yaWdodG1vc3RGYWlsdXJlUG9zaXRpb24pXG4gICAgICA6IC0xO1xuICB9XG5cbiAgLy8gUmV0dXJucyB0aGUgbWVtb2l6ZWQgdHJhY2UgZW50cnkgZm9yIGBleHByYCBhdCBgcG9zYCwgaWYgb25lIGV4aXN0cywgYG51bGxgIG90aGVyd2lzZS5cbiAgZ2V0TWVtb2l6ZWRUcmFjZUVudHJ5KHBvcywgZXhwcikge1xuICAgIGNvbnN0IHBvc0luZm8gPSB0aGlzLm1lbW9UYWJsZVtwb3NdO1xuICAgIGlmIChwb3NJbmZvICYmIGV4cHIgaW5zdGFuY2VvZiBwZXhwcnMuQXBwbHkpIHtcbiAgICAgIGNvbnN0IG1lbW9SZWMgPSBwb3NJbmZvLm1lbW9bZXhwci50b01lbW9LZXkoKV07XG4gICAgICBpZiAobWVtb1JlYyAmJiBtZW1vUmVjLnRyYWNlRW50cnkpIHtcbiAgICAgICAgY29uc3QgZW50cnkgPSBtZW1vUmVjLnRyYWNlRW50cnkuY2xvbmVXaXRoRXhwcihleHByKTtcbiAgICAgICAgZW50cnkuaXNNZW1vaXplZCA9IHRydWU7XG4gICAgICAgIHJldHVybiBlbnRyeTtcbiAgICAgIH1cbiAgICB9XG4gICAgcmV0dXJuIG51bGw7XG4gIH1cblxuICAvLyBSZXR1cm5zIGEgbmV3IHRyYWNlIGVudHJ5LCB3aXRoIHRoZSBjdXJyZW50bHkgYWN0aXZlIHRyYWNlIGFycmF5IGFzIGl0cyBjaGlsZHJlbi5cbiAgZ2V0VHJhY2VFbnRyeShwb3MsIGV4cHIsIHN1Y2NlZWRlZCwgYmluZGluZ3MpIHtcbiAgICBpZiAoZXhwciBpbnN0YW5jZW9mIHBleHBycy5BcHBseSkge1xuICAgICAgY29uc3QgYXBwID0gdGhpcy5jdXJyZW50QXBwbGljYXRpb24oKTtcbiAgICAgIGNvbnN0IGFjdHVhbHMgPSBhcHAgPyBhcHAuYXJncyA6IFtdO1xuICAgICAgZXhwciA9IGV4cHIuc3Vic3RpdHV0ZVBhcmFtcyhhY3R1YWxzKTtcbiAgICB9XG4gICAgcmV0dXJuIChcbiAgICAgIHRoaXMuZ2V0TWVtb2l6ZWRUcmFjZUVudHJ5KHBvcywgZXhwcikgfHxcbiAgICAgIG5ldyBUcmFjZSh0aGlzLmlucHV0LCBwb3MsIHRoaXMuaW5wdXRTdHJlYW0ucG9zLCBleHByLCBzdWNjZWVkZWQsIGJpbmRpbmdzLCB0aGlzLnRyYWNlKVxuICAgICk7XG4gIH1cblxuICBpc1RyYWNpbmcoKSB7XG4gICAgcmV0dXJuICEhdGhpcy50cmFjZTtcbiAgfVxuXG4gIGhhc05lY2Vzc2FyeUluZm8obWVtb1JlYykge1xuICAgIGlmICh0aGlzLnRyYWNlICYmICFtZW1vUmVjLnRyYWNlRW50cnkpIHtcbiAgICAgIHJldHVybiBmYWxzZTtcbiAgICB9XG5cbiAgICBpZiAoXG4gICAgICB0aGlzLnJlY29yZGVkRmFpbHVyZXMgJiZcbiAgICAgIHRoaXMuaW5wdXRTdHJlYW0ucG9zICsgbWVtb1JlYy5yaWdodG1vc3RGYWlsdXJlT2Zmc2V0ID09PSB0aGlzLnBvc2l0aW9uVG9SZWNvcmRGYWlsdXJlc1xuICAgICkge1xuICAgICAgcmV0dXJuICEhbWVtb1JlYy5mYWlsdXJlc0F0UmlnaHRtb3N0UG9zaXRpb247XG4gICAgfVxuXG4gICAgcmV0dXJuIHRydWU7XG4gIH1cblxuICB1c2VNZW1vaXplZFJlc3VsdChvcmlnUG9zLCBtZW1vUmVjKSB7XG4gICAgaWYgKHRoaXMudHJhY2UpIHtcbiAgICAgIHRoaXMudHJhY2UucHVzaChtZW1vUmVjLnRyYWNlRW50cnkpO1xuICAgIH1cblxuICAgIGNvbnN0IG1lbW9SZWNSaWdodG1vc3RGYWlsdXJlUG9zaXRpb24gPVxuICAgICAgdGhpcy5pbnB1dFN0cmVhbS5wb3MgKyBtZW1vUmVjLnJpZ2h0bW9zdEZhaWx1cmVPZmZzZXQ7XG4gICAgdGhpcy5yaWdodG1vc3RGYWlsdXJlUG9zaXRpb24gPSBNYXRoLm1heChcbiAgICAgIHRoaXMucmlnaHRtb3N0RmFpbHVyZVBvc2l0aW9uLFxuICAgICAgbWVtb1JlY1JpZ2h0bW9zdEZhaWx1cmVQb3NpdGlvblxuICAgICk7XG4gICAgaWYgKFxuICAgICAgdGhpcy5yZWNvcmRlZEZhaWx1cmVzICYmXG4gICAgICB0aGlzLnBvc2l0aW9uVG9SZWNvcmRGYWlsdXJlcyA9PT0gbWVtb1JlY1JpZ2h0bW9zdEZhaWx1cmVQb3NpdGlvbiAmJlxuICAgICAgbWVtb1JlYy5mYWlsdXJlc0F0UmlnaHRtb3N0UG9zaXRpb25cbiAgICApIHtcbiAgICAgIHRoaXMucmVjb3JkRmFpbHVyZXMobWVtb1JlYy5mYWlsdXJlc0F0UmlnaHRtb3N0UG9zaXRpb24sIHRydWUpO1xuICAgIH1cblxuICAgIHRoaXMuaW5wdXRTdHJlYW0uZXhhbWluZWRMZW5ndGggPSBNYXRoLm1heChcbiAgICAgIHRoaXMuaW5wdXRTdHJlYW0uZXhhbWluZWRMZW5ndGgsXG4gICAgICBtZW1vUmVjLmV4YW1pbmVkTGVuZ3RoICsgb3JpZ1Bvc1xuICAgICk7XG5cbiAgICBpZiAobWVtb1JlYy52YWx1ZSkge1xuICAgICAgdGhpcy5pbnB1dFN0cmVhbS5wb3MgKz0gbWVtb1JlYy5tYXRjaExlbmd0aDtcbiAgICAgIHRoaXMucHVzaEJpbmRpbmcobWVtb1JlYy52YWx1ZSwgb3JpZ1Bvcyk7XG4gICAgICByZXR1cm4gdHJ1ZTtcbiAgICB9XG4gICAgcmV0dXJuIGZhbHNlO1xuICB9XG5cbiAgLy8gRXZhbHVhdGUgYGV4cHJgIGFuZCByZXR1cm4gYHRydWVgIGlmIGl0IHN1Y2NlZWRlZCwgYGZhbHNlYCBvdGhlcndpc2UuIE9uIHN1Y2Nlc3MsIGBiaW5kaW5nc2BcbiAgLy8gd2lsbCBoYXZlIGBleHByLmdldEFyaXR5KClgIG1vcmUgZWxlbWVudHMgdGhhbiBiZWZvcmUsIGFuZCB0aGUgaW5wdXQgc3RyZWFtJ3MgcG9zaXRpb24gbWF5XG4gIC8vIGhhdmUgaW5jcmVhc2VkLiBPbiBmYWlsdXJlLCBgYmluZGluZ3NgIGFuZCBwb3NpdGlvbiB3aWxsIGJlIHVuY2hhbmdlZC5cbiAgZXZhbChleHByKSB7XG4gICAgY29uc3Qge2lucHV0U3RyZWFtfSA9IHRoaXM7XG4gICAgY29uc3Qgb3JpZ051bUJpbmRpbmdzID0gdGhpcy5fYmluZGluZ3MubGVuZ3RoO1xuICAgIGNvbnN0IG9yaWdVc2VyRGF0YSA9IHRoaXMudXNlckRhdGE7XG5cbiAgICBsZXQgb3JpZ1JlY29yZGVkRmFpbHVyZXM7XG4gICAgaWYgKHRoaXMucmVjb3JkZWRGYWlsdXJlcykge1xuICAgICAgb3JpZ1JlY29yZGVkRmFpbHVyZXMgPSB0aGlzLnJlY29yZGVkRmFpbHVyZXM7XG4gICAgICB0aGlzLnJlY29yZGVkRmFpbHVyZXMgPSBPYmplY3QuY3JlYXRlKG51bGwpO1xuICAgIH1cblxuICAgIGNvbnN0IG9yaWdQb3MgPSBpbnB1dFN0cmVhbS5wb3M7XG4gICAgY29uc3QgbWVtb1BvcyA9IHRoaXMubWF5YmVTa2lwU3BhY2VzQmVmb3JlKGV4cHIpO1xuXG4gICAgbGV0IG9yaWdUcmFjZTtcbiAgICBpZiAodGhpcy50cmFjZSkge1xuICAgICAgb3JpZ1RyYWNlID0gdGhpcy50cmFjZTtcbiAgICAgIHRoaXMudHJhY2UgPSBbXTtcbiAgICB9XG5cbiAgICAvLyBEbyB0aGUgYWN0dWFsIGV2YWx1YXRpb24uXG4gICAgY29uc3QgYW5zID0gZXhwci5ldmFsKHRoaXMpO1xuXG4gICAgaWYgKHRoaXMudHJhY2UpIHtcbiAgICAgIGNvbnN0IGJpbmRpbmdzID0gdGhpcy5fYmluZGluZ3Muc2xpY2Uob3JpZ051bUJpbmRpbmdzKTtcbiAgICAgIGNvbnN0IHRyYWNlRW50cnkgPSB0aGlzLmdldFRyYWNlRW50cnkobWVtb1BvcywgZXhwciwgYW5zLCBiaW5kaW5ncyk7XG4gICAgICB0cmFjZUVudHJ5LmlzSW1wbGljaXRTcGFjZXMgPSBleHByID09PSBhcHBseVNwYWNlcztcbiAgICAgIHRyYWNlRW50cnkuaXNSb290Tm9kZSA9IGV4cHIgPT09IHRoaXMuc3RhcnRFeHByO1xuICAgICAgb3JpZ1RyYWNlLnB1c2godHJhY2VFbnRyeSk7XG4gICAgICB0aGlzLnRyYWNlID0gb3JpZ1RyYWNlO1xuICAgIH1cblxuICAgIGlmIChhbnMpIHtcbiAgICAgIGlmICh0aGlzLnJlY29yZGVkRmFpbHVyZXMgJiYgaW5wdXRTdHJlYW0ucG9zID09PSB0aGlzLnBvc2l0aW9uVG9SZWNvcmRGYWlsdXJlcykge1xuICAgICAgICBPYmplY3Qua2V5cyh0aGlzLnJlY29yZGVkRmFpbHVyZXMpLmZvckVhY2goa2V5ID0+IHtcbiAgICAgICAgICB0aGlzLnJlY29yZGVkRmFpbHVyZXNba2V5XS5tYWtlRmx1ZmZ5KCk7XG4gICAgICAgIH0pO1xuICAgICAgfVxuICAgIH0gZWxzZSB7XG4gICAgICAvLyBSZXNldCB0aGUgcG9zaXRpb24sIGJpbmRpbmdzLCBhbmQgdXNlckRhdGEuXG4gICAgICBpbnB1dFN0cmVhbS5wb3MgPSBvcmlnUG9zO1xuICAgICAgdGhpcy50cnVuY2F0ZUJpbmRpbmdzKG9yaWdOdW1CaW5kaW5ncyk7XG4gICAgICB0aGlzLnVzZXJEYXRhID0gb3JpZ1VzZXJEYXRhO1xuICAgIH1cblxuICAgIGlmICh0aGlzLnJlY29yZGVkRmFpbHVyZXMpIHtcbiAgICAgIHRoaXMucmVjb3JkRmFpbHVyZXMob3JpZ1JlY29yZGVkRmFpbHVyZXMsIGZhbHNlKTtcbiAgICB9XG5cbiAgICAvLyBUaGUgYnVpbHQtaW4gYXBwbHlTeW50YWN0aWMgcnVsZSBuZWVkcyBzcGVjaWFsIGhhbmRsaW5nOiB3ZSB3YW50IHRvIHNraXBcbiAgICAvLyB0cmFpbGluZyBzcGFjZXMsIGp1c3QgYXMgd2l0aCB0aGUgdG9wLWxldmVsIGFwcGxpY2F0aW9uIG9mIGEgc3ludGFjdGljIHJ1bGUuXG4gICAgaWYgKGV4cHIgPT09IGJ1aWx0SW5BcHBseVN5bnRhY3RpY0JvZHkpIHtcbiAgICAgIHRoaXMuc2tpcFNwYWNlcygpO1xuICAgIH1cblxuICAgIHJldHVybiBhbnM7XG4gIH1cblxuICBnZXRNYXRjaFJlc3VsdCgpIHtcbiAgICB0aGlzLmdyYW1tYXIuX3NldFVwTWF0Y2hTdGF0ZSh0aGlzKTtcbiAgICB0aGlzLmV2YWwodGhpcy5zdGFydEV4cHIpO1xuICAgIGxldCByaWdodG1vc3RGYWlsdXJlcztcbiAgICBpZiAodGhpcy5yZWNvcmRlZEZhaWx1cmVzKSB7XG4gICAgICByaWdodG1vc3RGYWlsdXJlcyA9IE9iamVjdC5rZXlzKHRoaXMucmVjb3JkZWRGYWlsdXJlcykubWFwKFxuICAgICAgICBrZXkgPT4gdGhpcy5yZWNvcmRlZEZhaWx1cmVzW2tleV1cbiAgICAgICk7XG4gICAgfVxuICAgIGNvbnN0IGNzdCA9IHRoaXMuX2JpbmRpbmdzWzBdO1xuICAgIGlmIChjc3QpIHtcbiAgICAgIGNzdC5ncmFtbWFyID0gdGhpcy5ncmFtbWFyO1xuICAgIH1cbiAgICByZXR1cm4gbmV3IE1hdGNoUmVzdWx0KFxuICAgICAgdGhpcy5tYXRjaGVyLFxuICAgICAgdGhpcy5pbnB1dCxcbiAgICAgIHRoaXMuc3RhcnRFeHByLFxuICAgICAgY3N0LFxuICAgICAgdGhpcy5fYmluZGluZ09mZnNldHNbMF0sXG4gICAgICB0aGlzLnJpZ2h0bW9zdEZhaWx1cmVQb3NpdGlvbixcbiAgICAgIHJpZ2h0bW9zdEZhaWx1cmVzXG4gICAgKTtcbiAgfVxuXG4gIGdldFRyYWNlKCkge1xuICAgIHRoaXMudHJhY2UgPSBbXTtcbiAgICBjb25zdCBtYXRjaFJlc3VsdCA9IHRoaXMuZ2V0TWF0Y2hSZXN1bHQoKTtcblxuICAgIC8vIFRoZSB0cmFjZSBub2RlIGZvciB0aGUgc3RhcnQgcnVsZSBpcyBhbHdheXMgdGhlIGxhc3QgZW50cnkuIElmIGl0IGlzIGEgc3ludGFjdGljIHJ1bGUsXG4gICAgLy8gdGhlIGZpcnN0IGVudHJ5IGlzIGZvciBhbiBhcHBsaWNhdGlvbiBvZiAnc3BhY2VzJy5cbiAgICAvLyBUT0RPKHBkdWJyb3kpOiBDbGVhbiB0aGlzIHVwIGJ5IGludHJvZHVjaW5nIGEgc3BlY2lhbCBgTWF0Y2g8c3RhcnRBcHBsPmAgcnVsZSwgd2hpY2ggd2lsbFxuICAgIC8vIGVuc3VyZSB0aGF0IHRoZXJlIGlzIGFsd2F5cyBhIHNpbmdsZSByb290IHRyYWNlIG5vZGUuXG4gICAgY29uc3Qgcm9vdFRyYWNlID0gdGhpcy50cmFjZVt0aGlzLnRyYWNlLmxlbmd0aCAtIDFdO1xuICAgIHJvb3RUcmFjZS5yZXN1bHQgPSBtYXRjaFJlc3VsdDtcbiAgICByZXR1cm4gcm9vdFRyYWNlO1xuICB9XG5cbiAgcHVzaEZhaWx1cmVzSW5mbygpIHtcbiAgICB0aGlzLl9yaWdodG1vc3RGYWlsdXJlUG9zaXRpb25TdGFjay5wdXNoKHRoaXMucmlnaHRtb3N0RmFpbHVyZVBvc2l0aW9uKTtcbiAgICB0aGlzLl9yZWNvcmRlZEZhaWx1cmVzU3RhY2sucHVzaCh0aGlzLnJlY29yZGVkRmFpbHVyZXMpO1xuICB9XG5cbiAgcG9wRmFpbHVyZXNJbmZvKCkge1xuICAgIHRoaXMucmlnaHRtb3N0RmFpbHVyZVBvc2l0aW9uID0gdGhpcy5fcmlnaHRtb3N0RmFpbHVyZVBvc2l0aW9uU3RhY2sucG9wKCk7XG4gICAgdGhpcy5yZWNvcmRlZEZhaWx1cmVzID0gdGhpcy5fcmVjb3JkZWRGYWlsdXJlc1N0YWNrLnBvcCgpO1xuICB9XG59XG4iLCJpbXBvcnQge2dyYW1tYXJEb2VzTm90U3VwcG9ydEluY3JlbWVudGFsUGFyc2luZ30gZnJvbSAnLi9lcnJvcnMuanMnO1xuaW1wb3J0IHtNYXRjaFN0YXRlfSBmcm9tICcuL01hdGNoU3RhdGUuanMnO1xuaW1wb3J0ICogYXMgcGV4cHJzIGZyb20gJy4vcGV4cHJzLmpzJztcblxuZXhwb3J0IGNsYXNzIE1hdGNoZXIge1xuICBjb25zdHJ1Y3RvcihncmFtbWFyKSB7XG4gICAgdGhpcy5ncmFtbWFyID0gZ3JhbW1hcjtcbiAgICB0aGlzLl9tZW1vVGFibGUgPSBbXTtcbiAgICB0aGlzLl9pbnB1dCA9ICcnO1xuICAgIHRoaXMuX2lzTWVtb1RhYmxlU3RhbGUgPSBmYWxzZTtcbiAgfVxuXG4gIF9yZXNldE1lbW9UYWJsZSgpIHtcbiAgICB0aGlzLl9tZW1vVGFibGUgPSBbXTtcbiAgICB0aGlzLl9pc01lbW9UYWJsZVN0YWxlID0gZmFsc2U7XG4gIH1cblxuICBnZXRJbnB1dCgpIHtcbiAgICByZXR1cm4gdGhpcy5faW5wdXQ7XG4gIH1cblxuICBzZXRJbnB1dChzdHIpIHtcbiAgICBpZiAodGhpcy5faW5wdXQgIT09IHN0cikge1xuICAgICAgdGhpcy5yZXBsYWNlSW5wdXRSYW5nZSgwLCB0aGlzLl9pbnB1dC5sZW5ndGgsIHN0cik7XG4gICAgfVxuICAgIHJldHVybiB0aGlzO1xuICB9XG5cbiAgcmVwbGFjZUlucHV0UmFuZ2Uoc3RhcnRJZHgsIGVuZElkeCwgc3RyKSB7XG4gICAgY29uc3QgcHJldklucHV0ID0gdGhpcy5faW5wdXQ7XG4gICAgY29uc3QgbWVtb1RhYmxlID0gdGhpcy5fbWVtb1RhYmxlO1xuICAgIGlmIChcbiAgICAgIHN0YXJ0SWR4IDwgMCB8fFxuICAgICAgc3RhcnRJZHggPiBwcmV2SW5wdXQubGVuZ3RoIHx8XG4gICAgICBlbmRJZHggPCAwIHx8XG4gICAgICBlbmRJZHggPiBwcmV2SW5wdXQubGVuZ3RoIHx8XG4gICAgICBzdGFydElkeCA+IGVuZElkeFxuICAgICkge1xuICAgICAgdGhyb3cgbmV3IEVycm9yKCdJbnZhbGlkIGluZGljZXM6ICcgKyBzdGFydElkeCArICcgYW5kICcgKyBlbmRJZHgpO1xuICAgIH1cblxuICAgIC8vIHVwZGF0ZSBpbnB1dFxuICAgIHRoaXMuX2lucHV0ID0gcHJldklucHV0LnNsaWNlKDAsIHN0YXJ0SWR4KSArIHN0ciArIHByZXZJbnB1dC5zbGljZShlbmRJZHgpO1xuICAgIGlmICh0aGlzLl9pbnB1dCAhPT0gcHJldklucHV0ICYmIG1lbW9UYWJsZS5sZW5ndGggPiAwKSB7XG4gICAgICB0aGlzLl9pc01lbW9UYWJsZVN0YWxlID0gdHJ1ZTtcbiAgICB9XG5cbiAgICAvLyB1cGRhdGUgbWVtbyB0YWJsZSAoc2ltaWxhciB0byB0aGUgYWJvdmUpXG4gICAgY29uc3QgcmVzdE9mTWVtb1RhYmxlID0gbWVtb1RhYmxlLnNsaWNlKGVuZElkeCk7XG4gICAgbWVtb1RhYmxlLmxlbmd0aCA9IHN0YXJ0SWR4O1xuICAgIGZvciAobGV0IGlkeCA9IDA7IGlkeCA8IHN0ci5sZW5ndGg7IGlkeCsrKSB7XG4gICAgICBtZW1vVGFibGUucHVzaCh1bmRlZmluZWQpO1xuICAgIH1cbiAgICBmb3IgKGNvbnN0IHBvc0luZm8gb2YgcmVzdE9mTWVtb1RhYmxlKSB7XG4gICAgICBtZW1vVGFibGUucHVzaChwb3NJbmZvKTtcbiAgICB9XG5cbiAgICAvLyBJbnZhbGlkYXRlIG1lbW9SZWNzXG4gICAgZm9yIChsZXQgcG9zID0gMDsgcG9zIDwgc3RhcnRJZHg7IHBvcysrKSB7XG4gICAgICBjb25zdCBwb3NJbmZvID0gbWVtb1RhYmxlW3Bvc107XG4gICAgICBpZiAocG9zSW5mbykge1xuICAgICAgICBwb3NJbmZvLmNsZWFyT2Jzb2xldGVFbnRyaWVzKHBvcywgc3RhcnRJZHgpO1xuICAgICAgfVxuICAgIH1cblxuICAgIHJldHVybiB0aGlzO1xuICB9XG5cbiAgbWF0Y2gob3B0U3RhcnRBcHBsaWNhdGlvblN0ciwgb3B0aW9ucyA9IHtpbmNyZW1lbnRhbDogdHJ1ZX0pIHtcbiAgICByZXR1cm4gdGhpcy5fbWF0Y2godGhpcy5fZ2V0U3RhcnRFeHByKG9wdFN0YXJ0QXBwbGljYXRpb25TdHIpLCB7XG4gICAgICBpbmNyZW1lbnRhbDogb3B0aW9ucy5pbmNyZW1lbnRhbCxcbiAgICAgIHRyYWNpbmc6IGZhbHNlLFxuICAgIH0pO1xuICB9XG5cbiAgdHJhY2Uob3B0U3RhcnRBcHBsaWNhdGlvblN0ciwgb3B0aW9ucyA9IHtpbmNyZW1lbnRhbDogdHJ1ZX0pIHtcbiAgICByZXR1cm4gdGhpcy5fbWF0Y2godGhpcy5fZ2V0U3RhcnRFeHByKG9wdFN0YXJ0QXBwbGljYXRpb25TdHIpLCB7XG4gICAgICBpbmNyZW1lbnRhbDogb3B0aW9ucy5pbmNyZW1lbnRhbCxcbiAgICAgIHRyYWNpbmc6IHRydWUsXG4gICAgfSk7XG4gIH1cblxuICBfbWF0Y2goc3RhcnRFeHByLCBvcHRpb25zID0ge30pIHtcbiAgICBjb25zdCBvcHRzID0ge1xuICAgICAgdHJhY2luZzogZmFsc2UsXG4gICAgICBpbmNyZW1lbnRhbDogdHJ1ZSxcbiAgICAgIHBvc2l0aW9uVG9SZWNvcmRGYWlsdXJlczogdW5kZWZpbmVkLFxuICAgICAgLi4ub3B0aW9ucyxcbiAgICB9O1xuICAgIGlmICghb3B0cy5pbmNyZW1lbnRhbCkge1xuICAgICAgdGhpcy5fcmVzZXRNZW1vVGFibGUoKTtcbiAgICB9IGVsc2UgaWYgKHRoaXMuX2lzTWVtb1RhYmxlU3RhbGUgJiYgIXRoaXMuZ3JhbW1hci5zdXBwb3J0c0luY3JlbWVudGFsUGFyc2luZykge1xuICAgICAgdGhyb3cgZ3JhbW1hckRvZXNOb3RTdXBwb3J0SW5jcmVtZW50YWxQYXJzaW5nKHRoaXMuZ3JhbW1hcik7XG4gICAgfVxuXG4gICAgY29uc3Qgc3RhdGUgPSBuZXcgTWF0Y2hTdGF0ZSh0aGlzLCBzdGFydEV4cHIsIG9wdHMucG9zaXRpb25Ub1JlY29yZEZhaWx1cmVzKTtcbiAgICByZXR1cm4gb3B0cy50cmFjaW5nID8gc3RhdGUuZ2V0VHJhY2UoKSA6IHN0YXRlLmdldE1hdGNoUmVzdWx0KCk7XG4gIH1cblxuICAvKlxuICAgIFJldHVybnMgdGhlIHN0YXJ0aW5nIGV4cHJlc3Npb24gZm9yIHRoaXMgTWF0Y2hlcidzIGFzc29jaWF0ZWQgZ3JhbW1hci4gSWZcbiAgICBgb3B0U3RhcnRBcHBsaWNhdGlvblN0cmAgaXMgc3BlY2lmaWVkLCBpdCBpcyBhIHN0cmluZyBleHByZXNzaW5nIGEgcnVsZSBhcHBsaWNhdGlvbiBpbiB0aGVcbiAgICBncmFtbWFyLiBJZiBub3Qgc3BlY2lmaWVkLCB0aGUgZ3JhbW1hcidzIGRlZmF1bHQgc3RhcnQgcnVsZSB3aWxsIGJlIHVzZWQuXG4gICovXG4gIF9nZXRTdGFydEV4cHIob3B0U3RhcnRBcHBsaWNhdGlvblN0cikge1xuICAgIGNvbnN0IGFwcGxpY2F0aW9uU3RyID0gb3B0U3RhcnRBcHBsaWNhdGlvblN0ciB8fCB0aGlzLmdyYW1tYXIuZGVmYXVsdFN0YXJ0UnVsZTtcbiAgICBpZiAoIWFwcGxpY2F0aW9uU3RyKSB7XG4gICAgICB0aHJvdyBuZXcgRXJyb3IoJ01pc3Npbmcgc3RhcnQgcnVsZSBhcmd1bWVudCAtLSB0aGUgZ3JhbW1hciBoYXMgbm8gZGVmYXVsdCBzdGFydCBydWxlLicpO1xuICAgIH1cblxuICAgIGNvbnN0IHN0YXJ0QXBwID0gdGhpcy5ncmFtbWFyLnBhcnNlQXBwbGljYXRpb24oYXBwbGljYXRpb25TdHIpO1xuICAgIHJldHVybiBuZXcgcGV4cHJzLlNlcShbc3RhcnRBcHAsIHBleHBycy5lbmRdKTtcbiAgfVxufVxuIiwiaW1wb3J0IHtJbnB1dFN0cmVhbX0gZnJvbSAnLi9JbnB1dFN0cmVhbS5qcyc7XG5pbXBvcnQge0l0ZXJhdGlvbk5vZGV9IGZyb20gJy4vbm9kZXMuanMnO1xuaW1wb3J0IHtNYXRjaFJlc3VsdH0gZnJvbSAnLi9NYXRjaFJlc3VsdC5qcyc7XG5pbXBvcnQgKiBhcyBjb21tb24gZnJvbSAnLi9jb21tb24uanMnO1xuaW1wb3J0ICogYXMgZXJyb3JzIGZyb20gJy4vZXJyb3JzLmpzJztcbmltcG9ydCAqIGFzIHV0aWwgZnJvbSAnLi91dGlsLmpzJztcblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cbi8vIFByaXZhdGUgc3R1ZmZcbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG5cbmNvbnN0IGdsb2JhbEFjdGlvblN0YWNrID0gW107XG5cbmNvbnN0IGhhc093blByb3BlcnR5ID0gKHgsIHByb3ApID0+IE9iamVjdC5wcm90b3R5cGUuaGFzT3duUHJvcGVydHkuY2FsbCh4LCBwcm9wKTtcblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0gV3JhcHBlcnMgLS0tLS0tLS0tLS0tLS0tLS1cblxuLy8gV3JhcHBlcnMgZGVjb3JhdGUgQ1NUIG5vZGVzIHdpdGggYWxsIG9mIHRoZSBmdW5jdGlvbmFsaXR5IChpLmUuLCBvcGVyYXRpb25zIGFuZCBhdHRyaWJ1dGVzKVxuLy8gcHJvdmlkZWQgYnkgYSBTZW1hbnRpY3MgKHNlZSBiZWxvdykuIGBXcmFwcGVyYCBpcyB0aGUgYWJzdHJhY3Qgc3VwZXJjbGFzcyBvZiBhbGwgd3JhcHBlcnMuIEFcbi8vIGBXcmFwcGVyYCBtdXN0IGhhdmUgYF9ub2RlYCBhbmQgYF9zZW1hbnRpY3NgIGluc3RhbmNlIHZhcmlhYmxlcywgd2hpY2ggcmVmZXIgdG8gdGhlIENTVCBub2RlIGFuZFxuLy8gU2VtYW50aWNzIChyZXNwLikgZm9yIHdoaWNoIGl0IHdhcyBjcmVhdGVkLCBhbmQgYSBgX2NoaWxkV3JhcHBlcnNgIGluc3RhbmNlIHZhcmlhYmxlIHdoaWNoIGlzXG4vLyB1c2VkIHRvIGNhY2hlIHRoZSB3cmFwcGVyIGluc3RhbmNlcyB0aGF0IGFyZSBjcmVhdGVkIGZvciBpdHMgY2hpbGQgbm9kZXMuIFNldHRpbmcgdGhlc2UgaW5zdGFuY2Vcbi8vIHZhcmlhYmxlcyBpcyB0aGUgcmVzcG9uc2liaWxpdHkgb2YgdGhlIGNvbnN0cnVjdG9yIG9mIGVhY2ggU2VtYW50aWNzLXNwZWNpZmljIHN1YmNsYXNzIG9mXG4vLyBgV3JhcHBlcmAuXG5jbGFzcyBXcmFwcGVyIHtcbiAgY29uc3RydWN0b3Iobm9kZSwgc291cmNlSW50ZXJ2YWwsIGJhc2VJbnRlcnZhbCkge1xuICAgIHRoaXMuX25vZGUgPSBub2RlO1xuICAgIHRoaXMuc291cmNlID0gc291cmNlSW50ZXJ2YWw7XG5cbiAgICAvLyBUaGUgaW50ZXJ2YWwgdGhhdCB0aGUgY2hpbGRPZmZzZXRzIG9mIGBub2RlYCBhcmUgcmVsYXRpdmUgdG8uIEl0IHNob3VsZCBiZSB0aGUgc291cmNlXG4gICAgLy8gb2YgdGhlIGNsb3Nlc3QgTm9udGVybWluYWwgbm9kZS5cbiAgICB0aGlzLl9iYXNlSW50ZXJ2YWwgPSBiYXNlSW50ZXJ2YWw7XG5cbiAgICBpZiAobm9kZS5pc05vbnRlcm1pbmFsKCkpIHtcbiAgICAgIGNvbW1vbi5hc3NlcnQoc291cmNlSW50ZXJ2YWwgPT09IGJhc2VJbnRlcnZhbCk7XG4gICAgfVxuICAgIHRoaXMuX2NoaWxkV3JhcHBlcnMgPSBbXTtcbiAgfVxuXG4gIF9mb3JnZXRNZW1vaXplZFJlc3VsdEZvcihhdHRyaWJ1dGVOYW1lKSB7XG4gICAgLy8gUmVtb3ZlIHRoZSBtZW1vaXplZCBhdHRyaWJ1dGUgZnJvbSB0aGUgY3N0Tm9kZSBhbmQgYWxsIGl0cyBjaGlsZHJlbi5cbiAgICBkZWxldGUgdGhpcy5fbm9kZVt0aGlzLl9zZW1hbnRpY3MuYXR0cmlidXRlS2V5c1thdHRyaWJ1dGVOYW1lXV07XG4gICAgdGhpcy5jaGlsZHJlbi5mb3JFYWNoKGNoaWxkID0+IHtcbiAgICAgIGNoaWxkLl9mb3JnZXRNZW1vaXplZFJlc3VsdEZvcihhdHRyaWJ1dGVOYW1lKTtcbiAgICB9KTtcbiAgfVxuXG4gIC8vIFJldHVybnMgdGhlIHdyYXBwZXIgb2YgdGhlIHNwZWNpZmllZCBjaGlsZCBub2RlLiBDaGlsZCB3cmFwcGVycyBhcmUgY3JlYXRlZCBsYXppbHkgYW5kXG4gIC8vIGNhY2hlZCBpbiB0aGUgcGFyZW50IHdyYXBwZXIncyBgX2NoaWxkV3JhcHBlcnNgIGluc3RhbmNlIHZhcmlhYmxlLlxuICBjaGlsZChpZHgpIHtcbiAgICBpZiAoISgwIDw9IGlkeCAmJiBpZHggPCB0aGlzLl9ub2RlLm51bUNoaWxkcmVuKCkpKSB7XG4gICAgICAvLyBUT0RPOiBDb25zaWRlciB0aHJvd2luZyBhbiBleGNlcHRpb24gaGVyZS5cbiAgICAgIHJldHVybiB1bmRlZmluZWQ7XG4gICAgfVxuICAgIGxldCBjaGlsZFdyYXBwZXIgPSB0aGlzLl9jaGlsZFdyYXBwZXJzW2lkeF07XG4gICAgaWYgKCFjaGlsZFdyYXBwZXIpIHtcbiAgICAgIGNvbnN0IGNoaWxkTm9kZSA9IHRoaXMuX25vZGUuY2hpbGRBdChpZHgpO1xuICAgICAgY29uc3Qgb2Zmc2V0ID0gdGhpcy5fbm9kZS5jaGlsZE9mZnNldHNbaWR4XTtcblxuICAgICAgY29uc3Qgc291cmNlID0gdGhpcy5fYmFzZUludGVydmFsLnN1YkludGVydmFsKG9mZnNldCwgY2hpbGROb2RlLm1hdGNoTGVuZ3RoKTtcbiAgICAgIGNvbnN0IGJhc2UgPSBjaGlsZE5vZGUuaXNOb250ZXJtaW5hbCgpID8gc291cmNlIDogdGhpcy5fYmFzZUludGVydmFsO1xuICAgICAgY2hpbGRXcmFwcGVyID0gdGhpcy5fY2hpbGRXcmFwcGVyc1tpZHhdID0gdGhpcy5fc2VtYW50aWNzLndyYXAoY2hpbGROb2RlLCBzb3VyY2UsIGJhc2UpO1xuICAgIH1cbiAgICByZXR1cm4gY2hpbGRXcmFwcGVyO1xuICB9XG5cbiAgLy8gUmV0dXJucyBhbiBhcnJheSBjb250YWluaW5nIHRoZSB3cmFwcGVycyBvZiBhbGwgb2YgdGhlIGNoaWxkcmVuIG9mIHRoZSBub2RlIGFzc29jaWF0ZWRcbiAgLy8gd2l0aCB0aGlzIHdyYXBwZXIuXG4gIF9jaGlsZHJlbigpIHtcbiAgICAvLyBGb3JjZSB0aGUgY3JlYXRpb24gb2YgYWxsIGNoaWxkIHdyYXBwZXJzXG4gICAgZm9yIChsZXQgaWR4ID0gMDsgaWR4IDwgdGhpcy5fbm9kZS5udW1DaGlsZHJlbigpOyBpZHgrKykge1xuICAgICAgdGhpcy5jaGlsZChpZHgpO1xuICAgIH1cbiAgICByZXR1cm4gdGhpcy5fY2hpbGRXcmFwcGVycztcbiAgfVxuXG4gIC8vIFJldHVybnMgYHRydWVgIGlmIHRoZSBDU1Qgbm9kZSBhc3NvY2lhdGVkIHdpdGggdGhpcyB3cmFwcGVyIGNvcnJlc3BvbmRzIHRvIGFuIGl0ZXJhdGlvblxuICAvLyBleHByZXNzaW9uLCBpLmUuLCBhIEtsZWVuZS0qLCBLbGVlbmUtKywgb3IgYW4gb3B0aW9uYWwuIFJldHVybnMgYGZhbHNlYCBvdGhlcndpc2UuXG4gIGlzSXRlcmF0aW9uKCkge1xuICAgIHJldHVybiB0aGlzLl9ub2RlLmlzSXRlcmF0aW9uKCk7XG4gIH1cblxuICAvLyBSZXR1cm5zIGB0cnVlYCBpZiB0aGUgQ1NUIG5vZGUgYXNzb2NpYXRlZCB3aXRoIHRoaXMgd3JhcHBlciBpcyBhIHRlcm1pbmFsIG5vZGUsIGBmYWxzZWBcbiAgLy8gb3RoZXJ3aXNlLlxuICBpc1Rlcm1pbmFsKCkge1xuICAgIHJldHVybiB0aGlzLl9ub2RlLmlzVGVybWluYWwoKTtcbiAgfVxuXG4gIC8vIFJldHVybnMgYHRydWVgIGlmIHRoZSBDU1Qgbm9kZSBhc3NvY2lhdGVkIHdpdGggdGhpcyB3cmFwcGVyIGlzIGEgbm9udGVybWluYWwgbm9kZSwgYGZhbHNlYFxuICAvLyBvdGhlcndpc2UuXG4gIGlzTm9udGVybWluYWwoKSB7XG4gICAgcmV0dXJuIHRoaXMuX25vZGUuaXNOb250ZXJtaW5hbCgpO1xuICB9XG5cbiAgLy8gUmV0dXJucyBgdHJ1ZWAgaWYgdGhlIENTVCBub2RlIGFzc29jaWF0ZWQgd2l0aCB0aGlzIHdyYXBwZXIgaXMgYSBub250ZXJtaW5hbCBub2RlXG4gIC8vIGNvcnJlc3BvbmRpbmcgdG8gYSBzeW50YWN0aWMgcnVsZSwgYGZhbHNlYCBvdGhlcndpc2UuXG4gIGlzU3ludGFjdGljKCkge1xuICAgIHJldHVybiB0aGlzLmlzTm9udGVybWluYWwoKSAmJiB0aGlzLl9ub2RlLmlzU3ludGFjdGljKCk7XG4gIH1cblxuICAvLyBSZXR1cm5zIGB0cnVlYCBpZiB0aGUgQ1NUIG5vZGUgYXNzb2NpYXRlZCB3aXRoIHRoaXMgd3JhcHBlciBpcyBhIG5vbnRlcm1pbmFsIG5vZGVcbiAgLy8gY29ycmVzcG9uZGluZyB0byBhIGxleGljYWwgcnVsZSwgYGZhbHNlYCBvdGhlcndpc2UuXG4gIGlzTGV4aWNhbCgpIHtcbiAgICByZXR1cm4gdGhpcy5pc05vbnRlcm1pbmFsKCkgJiYgdGhpcy5fbm9kZS5pc0xleGljYWwoKTtcbiAgfVxuXG4gIC8vIFJldHVybnMgYHRydWVgIGlmIHRoZSBDU1Qgbm9kZSBhc3NvY2lhdGVkIHdpdGggdGhpcyB3cmFwcGVyIGlzIGFuIGl0ZXJhdG9yIG5vZGVcbiAgLy8gaGF2aW5nIGVpdGhlciBvbmUgb3Igbm8gY2hpbGQgKD8gb3BlcmF0b3IpLCBgZmFsc2VgIG90aGVyd2lzZS5cbiAgLy8gT3RoZXJ3aXNlLCB0aHJvd3MgYW4gZXhjZXB0aW9uLlxuICBpc09wdGlvbmFsKCkge1xuICAgIHJldHVybiB0aGlzLl9ub2RlLmlzT3B0aW9uYWwoKTtcbiAgfVxuXG4gIC8vIENyZWF0ZSBhIG5ldyBfaXRlciB3cmFwcGVyIGluIHRoZSBzYW1lIHNlbWFudGljcyBhcyB0aGlzIHdyYXBwZXIuXG4gIGl0ZXJhdGlvbihvcHRDaGlsZFdyYXBwZXJzKSB7XG4gICAgY29uc3QgY2hpbGRXcmFwcGVycyA9IG9wdENoaWxkV3JhcHBlcnMgfHwgW107XG5cbiAgICBjb25zdCBjaGlsZE5vZGVzID0gY2hpbGRXcmFwcGVycy5tYXAoYyA9PiBjLl9ub2RlKTtcbiAgICBjb25zdCBpdGVyID0gbmV3IEl0ZXJhdGlvbk5vZGUoY2hpbGROb2RlcywgW10sIC0xLCBmYWxzZSk7XG5cbiAgICBjb25zdCB3cmFwcGVyID0gdGhpcy5fc2VtYW50aWNzLndyYXAoaXRlciwgbnVsbCwgbnVsbCk7XG4gICAgd3JhcHBlci5fY2hpbGRXcmFwcGVycyA9IGNoaWxkV3JhcHBlcnM7XG4gICAgcmV0dXJuIHdyYXBwZXI7XG4gIH1cblxuICAvLyBSZXR1cm5zIGFuIGFycmF5IGNvbnRhaW5pbmcgdGhlIGNoaWxkcmVuIG9mIHRoaXMgQ1NUIG5vZGUuXG4gIGdldCBjaGlsZHJlbigpIHtcbiAgICByZXR1cm4gdGhpcy5fY2hpbGRyZW4oKTtcbiAgfVxuXG4gIC8vIFJldHVybnMgdGhlIG5hbWUgb2YgZ3JhbW1hciBydWxlIHRoYXQgY3JlYXRlZCB0aGlzIENTVCBub2RlLlxuICBnZXQgY3Rvck5hbWUoKSB7XG4gICAgcmV0dXJuIHRoaXMuX25vZGUuY3Rvck5hbWU7XG4gIH1cblxuICAvLyBSZXR1cm5zIHRoZSBudW1iZXIgb2YgY2hpbGRyZW4gb2YgdGhpcyBDU1Qgbm9kZS5cbiAgZ2V0IG51bUNoaWxkcmVuKCkge1xuICAgIHJldHVybiB0aGlzLl9ub2RlLm51bUNoaWxkcmVuKCk7XG4gIH1cblxuICAvLyBSZXR1cm5zIHRoZSBjb250ZW50cyBvZiB0aGUgaW5wdXQgc3RyZWFtIGNvbnN1bWVkIGJ5IHRoaXMgQ1NUIG5vZGUuXG4gIGdldCBzb3VyY2VTdHJpbmcoKSB7XG4gICAgcmV0dXJuIHRoaXMuc291cmNlLmNvbnRlbnRzO1xuICB9XG59XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tIFNlbWFudGljcyAtLS0tLS0tLS0tLS0tLS0tLVxuXG4vLyBBIFNlbWFudGljcyBpcyBhIGNvbnRhaW5lciBmb3IgYSBmYW1pbHkgb2YgT3BlcmF0aW9ucyBhbmQgQXR0cmlidXRlcyBmb3IgYSBnaXZlbiBncmFtbWFyLlxuLy8gU2VtYW50aWNzIGVuYWJsZSBtb2R1bGFyaXR5IChkaWZmZXJlbnQgY2xpZW50cyBvZiBhIGdyYW1tYXIgY2FuIGNyZWF0ZSB0aGVpciBzZXQgb2Ygb3BlcmF0aW9uc1xuLy8gYW5kIGF0dHJpYnV0ZXMgaW4gaXNvbGF0aW9uKSBhbmQgZXh0ZW5zaWJpbGl0eSBldmVuIHdoZW4gb3BlcmF0aW9ucyBhbmQgYXR0cmlidXRlcyBhcmUgbXV0dWFsbHktXG4vLyByZWN1cnNpdmUuIFRoaXMgY29uc3RydWN0b3Igc2hvdWxkIG5vdCBiZSBjYWxsZWQgZGlyZWN0bHkgZXhjZXB0IGZyb21cbi8vIGBTZW1hbnRpY3MuY3JlYXRlU2VtYW50aWNzYC4gVGhlIG5vcm1hbCB3YXlzIHRvIGNyZWF0ZSBhIFNlbWFudGljcywgZ2l2ZW4gYSBncmFtbWFyICdnJywgYXJlXG4vLyBgZy5jcmVhdGVTZW1hbnRpY3MoKWAgYW5kIGBnLmV4dGVuZFNlbWFudGljcyhwYXJlbnRTZW1hbnRpY3MpYC5cbmV4cG9ydCBjbGFzcyBTZW1hbnRpY3Mge1xuICBjb25zdHJ1Y3RvcihncmFtbWFyLCBzdXBlclNlbWFudGljcykge1xuICAgIGNvbnN0IHNlbGYgPSB0aGlzO1xuICAgIHRoaXMuZ3JhbW1hciA9IGdyYW1tYXI7XG4gICAgdGhpcy5jaGVja2VkQWN0aW9uRGljdHMgPSBmYWxzZTtcblxuICAgIC8vIENvbnN0cnVjdG9yIGZvciB3cmFwcGVyIGluc3RhbmNlcywgd2hpY2ggYXJlIHBhc3NlZCBhcyB0aGUgYXJndW1lbnRzIHRvIHRoZSBzZW1hbnRpYyBhY3Rpb25zXG4gICAgLy8gb2YgYW4gb3BlcmF0aW9uIG9yIGF0dHJpYnV0ZS4gT3BlcmF0aW9ucyBhbmQgYXR0cmlidXRlcyByZXF1aXJlIGRvdWJsZSBkaXNwYXRjaDogdGhlIHNlbWFudGljXG4gICAgLy8gYWN0aW9uIGlzIGNob3NlbiBiYXNlZCBvbiBib3RoIHRoZSBub2RlJ3MgdHlwZSBhbmQgdGhlIHNlbWFudGljcy4gV3JhcHBlcnMgZW5zdXJlIHRoYXRcbiAgICAvLyB0aGUgYGV4ZWN1dGVgIG1ldGhvZCBpcyBjYWxsZWQgd2l0aCB0aGUgY29ycmVjdCAobW9zdCBzcGVjaWZpYykgc2VtYW50aWNzIG9iamVjdCBhcyBhblxuICAgIC8vIGFyZ3VtZW50LlxuICAgIHRoaXMuV3JhcHBlciA9IGNsYXNzIGV4dGVuZHMgKHN1cGVyU2VtYW50aWNzID8gc3VwZXJTZW1hbnRpY3MuV3JhcHBlciA6IFdyYXBwZXIpIHtcbiAgICAgIGNvbnN0cnVjdG9yKG5vZGUsIHNvdXJjZUludGVydmFsLCBiYXNlSW50ZXJ2YWwpIHtcbiAgICAgICAgc3VwZXIobm9kZSwgc291cmNlSW50ZXJ2YWwsIGJhc2VJbnRlcnZhbCk7XG4gICAgICAgIHNlbGYuY2hlY2tBY3Rpb25EaWN0c0lmSGF2ZW50QWxyZWFkeSgpO1xuICAgICAgICB0aGlzLl9zZW1hbnRpY3MgPSBzZWxmO1xuICAgICAgfVxuXG4gICAgICB0b1N0cmluZygpIHtcbiAgICAgICAgcmV0dXJuICdbc2VtYW50aWNzIHdyYXBwZXIgZm9yICcgKyBzZWxmLmdyYW1tYXIubmFtZSArICddJztcbiAgICAgIH1cbiAgICB9O1xuXG4gICAgdGhpcy5zdXBlciA9IHN1cGVyU2VtYW50aWNzO1xuICAgIGlmIChzdXBlclNlbWFudGljcykge1xuICAgICAgaWYgKCEoZ3JhbW1hci5lcXVhbHModGhpcy5zdXBlci5ncmFtbWFyKSB8fCBncmFtbWFyLl9pbmhlcml0c0Zyb20odGhpcy5zdXBlci5ncmFtbWFyKSkpIHtcbiAgICAgICAgdGhyb3cgbmV3IEVycm9yKFxuICAgICAgICAgIFwiQ2Fubm90IGV4dGVuZCBhIHNlbWFudGljcyBmb3IgZ3JhbW1hciAnXCIgK1xuICAgICAgICAgICAgdGhpcy5zdXBlci5ncmFtbWFyLm5hbWUgK1xuICAgICAgICAgICAgXCInIGZvciB1c2Ugd2l0aCBncmFtbWFyICdcIiArXG4gICAgICAgICAgICBncmFtbWFyLm5hbWUgK1xuICAgICAgICAgICAgXCInIChub3QgYSBzdWItZ3JhbW1hcilcIlxuICAgICAgICApO1xuICAgICAgfVxuICAgICAgdGhpcy5vcGVyYXRpb25zID0gT2JqZWN0LmNyZWF0ZSh0aGlzLnN1cGVyLm9wZXJhdGlvbnMpO1xuICAgICAgdGhpcy5hdHRyaWJ1dGVzID0gT2JqZWN0LmNyZWF0ZSh0aGlzLnN1cGVyLmF0dHJpYnV0ZXMpO1xuICAgICAgdGhpcy5hdHRyaWJ1dGVLZXlzID0gT2JqZWN0LmNyZWF0ZShudWxsKTtcblxuICAgICAgLy8gQXNzaWduIHVuaXF1ZSBzeW1ib2xzIGZvciBlYWNoIG9mIHRoZSBhdHRyaWJ1dGVzIGluaGVyaXRlZCBmcm9tIHRoZSBzdXBlci1zZW1hbnRpY3Mgc28gdGhhdFxuICAgICAgLy8gdGhleSBhcmUgbWVtb2l6ZWQgaW5kZXBlbmRlbnRseS5cblxuICAgICAgZm9yIChjb25zdCBhdHRyaWJ1dGVOYW1lIGluIHRoaXMuYXR0cmlidXRlcykge1xuICAgICAgICBPYmplY3QuZGVmaW5lUHJvcGVydHkodGhpcy5hdHRyaWJ1dGVLZXlzLCBhdHRyaWJ1dGVOYW1lLCB7XG4gICAgICAgICAgdmFsdWU6IHV0aWwudW5pcXVlSWQoYXR0cmlidXRlTmFtZSksXG4gICAgICAgIH0pO1xuICAgICAgfVxuICAgIH0gZWxzZSB7XG4gICAgICB0aGlzLm9wZXJhdGlvbnMgPSBPYmplY3QuY3JlYXRlKG51bGwpO1xuICAgICAgdGhpcy5hdHRyaWJ1dGVzID0gT2JqZWN0LmNyZWF0ZShudWxsKTtcbiAgICAgIHRoaXMuYXR0cmlidXRlS2V5cyA9IE9iamVjdC5jcmVhdGUobnVsbCk7XG4gICAgfVxuICB9XG5cbiAgdG9TdHJpbmcoKSB7XG4gICAgcmV0dXJuICdbc2VtYW50aWNzIGZvciAnICsgdGhpcy5ncmFtbWFyLm5hbWUgKyAnXSc7XG4gIH1cblxuICBjaGVja0FjdGlvbkRpY3RzSWZIYXZlbnRBbHJlYWR5KCkge1xuICAgIGlmICghdGhpcy5jaGVja2VkQWN0aW9uRGljdHMpIHtcbiAgICAgIHRoaXMuY2hlY2tBY3Rpb25EaWN0cygpO1xuICAgICAgdGhpcy5jaGVja2VkQWN0aW9uRGljdHMgPSB0cnVlO1xuICAgIH1cbiAgfVxuXG4gIC8vIENoZWNrcyB0aGF0IHRoZSBhY3Rpb24gZGljdGlvbmFyaWVzIGZvciBhbGwgb3BlcmF0aW9ucyBhbmQgYXR0cmlidXRlcyBpbiB0aGlzIHNlbWFudGljcyxcbiAgLy8gaW5jbHVkaW5nIHRoZSBvbmVzIHRoYXQgd2VyZSBpbmhlcml0ZWQgZnJvbSB0aGUgc3VwZXItc2VtYW50aWNzLCBhZ3JlZSB3aXRoIHRoZSBncmFtbWFyLlxuICAvLyBUaHJvd3MgYW4gZXhjZXB0aW9uIGlmIG9uZSBvciBtb3JlIG9mIHRoZW0gZG9lc24ndC5cbiAgY2hlY2tBY3Rpb25EaWN0cygpIHtcbiAgICBsZXQgbmFtZTtcblxuICAgIGZvciAobmFtZSBpbiB0aGlzLm9wZXJhdGlvbnMpIHtcbiAgICAgIHRoaXMub3BlcmF0aW9uc1tuYW1lXS5jaGVja0FjdGlvbkRpY3QodGhpcy5ncmFtbWFyKTtcbiAgICB9XG5cbiAgICBmb3IgKG5hbWUgaW4gdGhpcy5hdHRyaWJ1dGVzKSB7XG4gICAgICB0aGlzLmF0dHJpYnV0ZXNbbmFtZV0uY2hlY2tBY3Rpb25EaWN0KHRoaXMuZ3JhbW1hcik7XG4gICAgfVxuICB9XG5cbiAgdG9SZWNpcGUoc2VtYW50aWNzT25seSkge1xuICAgIGZ1bmN0aW9uIGhhc1N1cGVyU2VtYW50aWNzKHMpIHtcbiAgICAgIHJldHVybiBzLnN1cGVyICE9PSBTZW1hbnRpY3MuQnVpbHRJblNlbWFudGljcy5fZ2V0U2VtYW50aWNzKCk7XG4gICAgfVxuXG4gICAgbGV0IHN0ciA9ICcoZnVuY3Rpb24oZykge1xcbic7XG4gICAgaWYgKGhhc1N1cGVyU2VtYW50aWNzKHRoaXMpKSB7XG4gICAgICBzdHIgKz0gJyAgdmFyIHNlbWFudGljcyA9ICcgKyB0aGlzLnN1cGVyLnRvUmVjaXBlKHRydWUpICsgJyhnJztcblxuICAgICAgY29uc3Qgc3VwZXJTZW1hbnRpY3NHcmFtbWFyID0gdGhpcy5zdXBlci5ncmFtbWFyO1xuICAgICAgbGV0IHJlbGF0ZWRHcmFtbWFyID0gdGhpcy5ncmFtbWFyO1xuICAgICAgd2hpbGUgKHJlbGF0ZWRHcmFtbWFyICE9PSBzdXBlclNlbWFudGljc0dyYW1tYXIpIHtcbiAgICAgICAgc3RyICs9ICcuc3VwZXJHcmFtbWFyJztcbiAgICAgICAgcmVsYXRlZEdyYW1tYXIgPSByZWxhdGVkR3JhbW1hci5zdXBlckdyYW1tYXI7XG4gICAgICB9XG5cbiAgICAgIHN0ciArPSAnKTtcXG4nO1xuICAgICAgc3RyICs9ICcgIHJldHVybiBnLmV4dGVuZFNlbWFudGljcyhzZW1hbnRpY3MpJztcbiAgICB9IGVsc2Uge1xuICAgICAgc3RyICs9ICcgIHJldHVybiBnLmNyZWF0ZVNlbWFudGljcygpJztcbiAgICB9XG4gICAgWydPcGVyYXRpb24nLCAnQXR0cmlidXRlJ10uZm9yRWFjaCh0eXBlID0+IHtcbiAgICAgIGNvbnN0IHNlbWFudGljT3BlcmF0aW9ucyA9IHRoaXNbdHlwZS50b0xvd2VyQ2FzZSgpICsgJ3MnXTtcbiAgICAgIE9iamVjdC5rZXlzKHNlbWFudGljT3BlcmF0aW9ucykuZm9yRWFjaChuYW1lID0+IHtcbiAgICAgICAgY29uc3Qge2FjdGlvbkRpY3QsIGZvcm1hbHMsIGJ1aWx0SW5EZWZhdWx0fSA9IHNlbWFudGljT3BlcmF0aW9uc1tuYW1lXTtcblxuICAgICAgICBsZXQgc2lnbmF0dXJlID0gbmFtZTtcbiAgICAgICAgaWYgKGZvcm1hbHMubGVuZ3RoID4gMCkge1xuICAgICAgICAgIHNpZ25hdHVyZSArPSAnKCcgKyBmb3JtYWxzLmpvaW4oJywgJykgKyAnKSc7XG4gICAgICAgIH1cblxuICAgICAgICBsZXQgbWV0aG9kO1xuICAgICAgICBpZiAoaGFzU3VwZXJTZW1hbnRpY3ModGhpcykgJiYgdGhpcy5zdXBlclt0eXBlLnRvTG93ZXJDYXNlKCkgKyAncyddW25hbWVdKSB7XG4gICAgICAgICAgbWV0aG9kID0gJ2V4dGVuZCcgKyB0eXBlO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIG1ldGhvZCA9ICdhZGQnICsgdHlwZTtcbiAgICAgICAgfVxuICAgICAgICBzdHIgKz0gJ1xcbiAgICAuJyArIG1ldGhvZCArICcoJyArIEpTT04uc3RyaW5naWZ5KHNpZ25hdHVyZSkgKyAnLCB7JztcblxuICAgICAgICBjb25zdCBzcmNBcnJheSA9IFtdO1xuICAgICAgICBPYmplY3Qua2V5cyhhY3Rpb25EaWN0KS5mb3JFYWNoKGFjdGlvbk5hbWUgPT4ge1xuICAgICAgICAgIGlmIChhY3Rpb25EaWN0W2FjdGlvbk5hbWVdICE9PSBidWlsdEluRGVmYXVsdCkge1xuICAgICAgICAgICAgbGV0IHNvdXJjZSA9IGFjdGlvbkRpY3RbYWN0aW9uTmFtZV0udG9TdHJpbmcoKS50cmltKCk7XG5cbiAgICAgICAgICAgIC8vIENvbnZlcnQgbWV0aG9kIHNob3J0aGFuZCB0byBwbGFpbiBvbGQgZnVuY3Rpb24gc3ludGF4LlxuICAgICAgICAgICAgLy8gaHR0cHM6Ly9naXRodWIuY29tL29obWpzL29obS9pc3N1ZXMvMjYzXG4gICAgICAgICAgICBzb3VyY2UgPSBzb3VyY2UucmVwbGFjZSgvXi4qXFwoLywgJ2Z1bmN0aW9uKCcpO1xuXG4gICAgICAgICAgICBzcmNBcnJheS5wdXNoKCdcXG4gICAgICAnICsgSlNPTi5zdHJpbmdpZnkoYWN0aW9uTmFtZSkgKyAnOiAnICsgc291cmNlKTtcbiAgICAgICAgICB9XG4gICAgICAgIH0pO1xuICAgICAgICBzdHIgKz0gc3JjQXJyYXkuam9pbignLCcpICsgJ1xcbiAgICB9KSc7XG4gICAgICB9KTtcbiAgICB9KTtcbiAgICBzdHIgKz0gJztcXG4gIH0pJztcblxuICAgIGlmICghc2VtYW50aWNzT25seSkge1xuICAgICAgc3RyID1cbiAgICAgICAgJyhmdW5jdGlvbigpIHtcXG4nICtcbiAgICAgICAgJyAgdmFyIGdyYW1tYXIgPSB0aGlzLmZyb21SZWNpcGUoJyArXG4gICAgICAgIHRoaXMuZ3JhbW1hci50b1JlY2lwZSgpICtcbiAgICAgICAgJyk7XFxuJyArXG4gICAgICAgICcgIHZhciBzZW1hbnRpY3MgPSAnICtcbiAgICAgICAgc3RyICtcbiAgICAgICAgJyhncmFtbWFyKTtcXG4nICtcbiAgICAgICAgJyAgcmV0dXJuIHNlbWFudGljcztcXG4nICtcbiAgICAgICAgJ30pO1xcbic7XG4gICAgfVxuXG4gICAgcmV0dXJuIHN0cjtcbiAgfVxuXG4gIGFkZE9wZXJhdGlvbk9yQXR0cmlidXRlKHR5cGUsIHNpZ25hdHVyZSwgYWN0aW9uRGljdCkge1xuICAgIGNvbnN0IHR5cGVQbHVyYWwgPSB0eXBlICsgJ3MnO1xuXG4gICAgY29uc3QgcGFyc2VkTmFtZUFuZEZvcm1hbEFyZ3MgPSBwYXJzZVNpZ25hdHVyZShzaWduYXR1cmUsIHR5cGUpO1xuICAgIGNvbnN0IHtuYW1lfSA9IHBhcnNlZE5hbWVBbmRGb3JtYWxBcmdzO1xuICAgIGNvbnN0IHtmb3JtYWxzfSA9IHBhcnNlZE5hbWVBbmRGb3JtYWxBcmdzO1xuXG4gICAgLy8gVE9ETzogY2hlY2sgdGhhdCB0aGVyZSBhcmUgbm8gZHVwbGljYXRlIGZvcm1hbCBhcmd1bWVudHNcblxuICAgIHRoaXMuYXNzZXJ0TmV3TmFtZShuYW1lLCB0eXBlKTtcblxuICAgIC8vIENyZWF0ZSB0aGUgYWN0aW9uIGRpY3Rpb25hcnkgZm9yIHRoaXMgb3BlcmF0aW9uIC8gYXR0cmlidXRlIHRoYXQgY29udGFpbnMgYSBgX2RlZmF1bHRgIGFjdGlvblxuICAgIC8vIHdoaWNoIGRlZmluZXMgdGhlIGRlZmF1bHQgYmVoYXZpb3Igb2YgaXRlcmF0aW9uLCB0ZXJtaW5hbCwgYW5kIG5vbi10ZXJtaW5hbCBub2Rlcy4uLlxuICAgIGNvbnN0IGJ1aWx0SW5EZWZhdWx0ID0gbmV3RGVmYXVsdEFjdGlvbih0eXBlLCBuYW1lLCBkb0l0KTtcbiAgICBjb25zdCByZWFsQWN0aW9uRGljdCA9IHtfZGVmYXVsdDogYnVpbHRJbkRlZmF1bHR9O1xuICAgIC8vIC4uLiBhbmQgYWRkIGluIHRoZSBhY3Rpb25zIHN1cHBsaWVkIGJ5IHRoZSBwcm9ncmFtbWVyLCB3aGljaCBtYXkgb3ZlcnJpZGUgc29tZSBvciBhbGwgb2YgdGhlXG4gICAgLy8gZGVmYXVsdCBvbmVzLlxuICAgIE9iamVjdC5rZXlzKGFjdGlvbkRpY3QpLmZvckVhY2gobmFtZSA9PiB7XG4gICAgICByZWFsQWN0aW9uRGljdFtuYW1lXSA9IGFjdGlvbkRpY3RbbmFtZV07XG4gICAgfSk7XG5cbiAgICBjb25zdCBlbnRyeSA9XG4gICAgICB0eXBlID09PSAnb3BlcmF0aW9uJ1xuICAgICAgICA/IG5ldyBPcGVyYXRpb24obmFtZSwgZm9ybWFscywgcmVhbEFjdGlvbkRpY3QsIGJ1aWx0SW5EZWZhdWx0KVxuICAgICAgICA6IG5ldyBBdHRyaWJ1dGUobmFtZSwgcmVhbEFjdGlvbkRpY3QsIGJ1aWx0SW5EZWZhdWx0KTtcblxuICAgIC8vIFRoZSBmb2xsb3dpbmcgY2hlY2sgaXMgbm90IHN0cmljdGx5IG5lY2Vzc2FyeSAoaXQgd2lsbCBoYXBwZW4gbGF0ZXIgYW55d2F5KSBidXQgaXQncyBiZXR0ZXJcbiAgICAvLyB0byBjYXRjaCBlcnJvcnMgZWFybHkuXG4gICAgZW50cnkuY2hlY2tBY3Rpb25EaWN0KHRoaXMuZ3JhbW1hcik7XG5cbiAgICB0aGlzW3R5cGVQbHVyYWxdW25hbWVdID0gZW50cnk7XG5cbiAgICBmdW5jdGlvbiBkb0l0KC4uLmFyZ3MpIHtcbiAgICAgIC8vIERpc3BhdGNoIHRvIG1vc3Qgc3BlY2lmaWMgdmVyc2lvbiBvZiB0aGlzIG9wZXJhdGlvbiAvIGF0dHJpYnV0ZSAtLSBpdCBtYXkgaGF2ZSBiZWVuXG4gICAgICAvLyBvdmVycmlkZGVuIGJ5IGEgc3ViLXNlbWFudGljcy5cbiAgICAgIGNvbnN0IHRoaXNUaGluZyA9IHRoaXMuX3NlbWFudGljc1t0eXBlUGx1cmFsXVtuYW1lXTtcblxuICAgICAgLy8gQ2hlY2sgdGhhdCB0aGUgY2FsbGVyIHBhc3NlZCB0aGUgY29ycmVjdCBudW1iZXIgb2YgYXJndW1lbnRzLlxuICAgICAgaWYgKGFyZ3VtZW50cy5sZW5ndGggIT09IHRoaXNUaGluZy5mb3JtYWxzLmxlbmd0aCkge1xuICAgICAgICB0aHJvdyBuZXcgRXJyb3IoXG4gICAgICAgICAgJ0ludmFsaWQgbnVtYmVyIG9mIGFyZ3VtZW50cyBwYXNzZWQgdG8gJyArXG4gICAgICAgICAgICBuYW1lICtcbiAgICAgICAgICAgICcgJyArXG4gICAgICAgICAgICB0eXBlICtcbiAgICAgICAgICAgICcgKGV4cGVjdGVkICcgK1xuICAgICAgICAgICAgdGhpc1RoaW5nLmZvcm1hbHMubGVuZ3RoICtcbiAgICAgICAgICAgICcsIGdvdCAnICtcbiAgICAgICAgICAgIGFyZ3VtZW50cy5sZW5ndGggK1xuICAgICAgICAgICAgJyknXG4gICAgICAgICk7XG4gICAgICB9XG5cbiAgICAgIC8vIENyZWF0ZSBhbiBcImFyZ3VtZW50cyBvYmplY3RcIiBmcm9tIHRoZSBhcmd1bWVudHMgdGhhdCB3ZXJlIHBhc3NlZCB0byB0aGlzXG4gICAgICAvLyBvcGVyYXRpb24gLyBhdHRyaWJ1dGUuXG4gICAgICBjb25zdCBhcmdzT2JqID0gT2JqZWN0LmNyZWF0ZShudWxsKTtcbiAgICAgIGZvciAoY29uc3QgW2lkeCwgdmFsXSBvZiBPYmplY3QuZW50cmllcyhhcmdzKSkge1xuICAgICAgICBjb25zdCBmb3JtYWwgPSB0aGlzVGhpbmcuZm9ybWFsc1tpZHhdO1xuICAgICAgICBhcmdzT2JqW2Zvcm1hbF0gPSB2YWw7XG4gICAgICB9XG5cbiAgICAgIGNvbnN0IG9sZEFyZ3MgPSB0aGlzLmFyZ3M7XG4gICAgICB0aGlzLmFyZ3MgPSBhcmdzT2JqO1xuICAgICAgY29uc3QgYW5zID0gdGhpc1RoaW5nLmV4ZWN1dGUodGhpcy5fc2VtYW50aWNzLCB0aGlzKTtcbiAgICAgIHRoaXMuYXJncyA9IG9sZEFyZ3M7XG4gICAgICByZXR1cm4gYW5zO1xuICAgIH1cblxuICAgIGlmICh0eXBlID09PSAnb3BlcmF0aW9uJykge1xuICAgICAgdGhpcy5XcmFwcGVyLnByb3RvdHlwZVtuYW1lXSA9IGRvSXQ7XG4gICAgICB0aGlzLldyYXBwZXIucHJvdG90eXBlW25hbWVdLnRvU3RyaW5nID0gZnVuY3Rpb24gKCkge1xuICAgICAgICByZXR1cm4gJ1snICsgbmFtZSArICcgb3BlcmF0aW9uXSc7XG4gICAgICB9O1xuICAgIH0gZWxzZSB7XG4gICAgICBPYmplY3QuZGVmaW5lUHJvcGVydHkodGhpcy5XcmFwcGVyLnByb3RvdHlwZSwgbmFtZSwge1xuICAgICAgICBnZXQ6IGRvSXQsXG4gICAgICAgIGNvbmZpZ3VyYWJsZTogdHJ1ZSwgLy8gU28gdGhlIHByb3BlcnR5IGNhbiBiZSBkZWxldGVkLlxuICAgICAgfSk7XG4gICAgICBPYmplY3QuZGVmaW5lUHJvcGVydHkodGhpcy5hdHRyaWJ1dGVLZXlzLCBuYW1lLCB7XG4gICAgICAgIHZhbHVlOiB1dGlsLnVuaXF1ZUlkKG5hbWUpLFxuICAgICAgfSk7XG4gICAgfVxuICB9XG5cbiAgZXh0ZW5kT3BlcmF0aW9uT3JBdHRyaWJ1dGUodHlwZSwgbmFtZSwgYWN0aW9uRGljdCkge1xuICAgIGNvbnN0IHR5cGVQbHVyYWwgPSB0eXBlICsgJ3MnO1xuXG4gICAgLy8gTWFrZSBzdXJlIHRoYXQgYG5hbWVgIHJlYWxseSBpcyBqdXN0IGEgbmFtZSwgaS5lLiwgdGhhdCBpdCBkb2Vzbid0IGFsc28gY29udGFpbiBmb3JtYWxzLlxuICAgIHBhcnNlU2lnbmF0dXJlKG5hbWUsICdhdHRyaWJ1dGUnKTtcblxuICAgIGlmICghKHRoaXMuc3VwZXIgJiYgbmFtZSBpbiB0aGlzLnN1cGVyW3R5cGVQbHVyYWxdKSkge1xuICAgICAgdGhyb3cgbmV3IEVycm9yKFxuICAgICAgICAnQ2Fubm90IGV4dGVuZCAnICtcbiAgICAgICAgICB0eXBlICtcbiAgICAgICAgICBcIiAnXCIgK1xuICAgICAgICAgIG5hbWUgK1xuICAgICAgICAgIFwiJzogZGlkIG5vdCBpbmhlcml0IGFuIFwiICtcbiAgICAgICAgICB0eXBlICtcbiAgICAgICAgICAnIHdpdGggdGhhdCBuYW1lJ1xuICAgICAgKTtcbiAgICB9XG4gICAgaWYgKGhhc093blByb3BlcnR5KHRoaXNbdHlwZVBsdXJhbF0sIG5hbWUpKSB7XG4gICAgICB0aHJvdyBuZXcgRXJyb3IoJ0Nhbm5vdCBleHRlbmQgJyArIHR5cGUgKyBcIiAnXCIgKyBuYW1lICsgXCInIGFnYWluXCIpO1xuICAgIH1cblxuICAgIC8vIENyZWF0ZSBhIG5ldyBvcGVyYXRpb24gLyBhdHRyaWJ1dGUgd2hvc2UgYWN0aW9uRGljdCBkZWxlZ2F0ZXMgdG8gdGhlIHN1cGVyIG9wZXJhdGlvbiAvXG4gICAgLy8gYXR0cmlidXRlJ3MgYWN0aW9uRGljdCwgYW5kIHdoaWNoIGhhcyBhbGwgdGhlIGtleXMgZnJvbSBgaW5oZXJpdGVkQWN0aW9uRGljdGAuXG4gICAgY29uc3QgaW5oZXJpdGVkRm9ybWFscyA9IHRoaXNbdHlwZVBsdXJhbF1bbmFtZV0uZm9ybWFscztcbiAgICBjb25zdCBpbmhlcml0ZWRBY3Rpb25EaWN0ID0gdGhpc1t0eXBlUGx1cmFsXVtuYW1lXS5hY3Rpb25EaWN0O1xuICAgIGNvbnN0IG5ld0FjdGlvbkRpY3QgPSBPYmplY3QuY3JlYXRlKGluaGVyaXRlZEFjdGlvbkRpY3QpO1xuICAgIE9iamVjdC5rZXlzKGFjdGlvbkRpY3QpLmZvckVhY2gobmFtZSA9PiB7XG4gICAgICBuZXdBY3Rpb25EaWN0W25hbWVdID0gYWN0aW9uRGljdFtuYW1lXTtcbiAgICB9KTtcblxuICAgIHRoaXNbdHlwZVBsdXJhbF1bbmFtZV0gPVxuICAgICAgdHlwZSA9PT0gJ29wZXJhdGlvbidcbiAgICAgICAgPyBuZXcgT3BlcmF0aW9uKG5hbWUsIGluaGVyaXRlZEZvcm1hbHMsIG5ld0FjdGlvbkRpY3QpXG4gICAgICAgIDogbmV3IEF0dHJpYnV0ZShuYW1lLCBuZXdBY3Rpb25EaWN0KTtcblxuICAgIC8vIFRoZSBmb2xsb3dpbmcgY2hlY2sgaXMgbm90IHN0cmljdGx5IG5lY2Vzc2FyeSAoaXQgd2lsbCBoYXBwZW4gbGF0ZXIgYW55d2F5KSBidXQgaXQncyBiZXR0ZXJcbiAgICAvLyB0byBjYXRjaCBlcnJvcnMgZWFybHkuXG4gICAgdGhpc1t0eXBlUGx1cmFsXVtuYW1lXS5jaGVja0FjdGlvbkRpY3QodGhpcy5ncmFtbWFyKTtcbiAgfVxuXG4gIGFzc2VydE5ld05hbWUobmFtZSwgdHlwZSkge1xuICAgIGlmIChoYXNPd25Qcm9wZXJ0eShXcmFwcGVyLnByb3RvdHlwZSwgbmFtZSkpIHtcbiAgICAgIHRocm93IG5ldyBFcnJvcignQ2Fubm90IGFkZCAnICsgdHlwZSArIFwiICdcIiArIG5hbWUgKyBcIic6IHRoYXQncyBhIHJlc2VydmVkIG5hbWVcIik7XG4gICAgfVxuICAgIGlmIChuYW1lIGluIHRoaXMub3BlcmF0aW9ucykge1xuICAgICAgdGhyb3cgbmV3IEVycm9yKFxuICAgICAgICAnQ2Fubm90IGFkZCAnICsgdHlwZSArIFwiICdcIiArIG5hbWUgKyBcIic6IGFuIG9wZXJhdGlvbiB3aXRoIHRoYXQgbmFtZSBhbHJlYWR5IGV4aXN0c1wiXG4gICAgICApO1xuICAgIH1cbiAgICBpZiAobmFtZSBpbiB0aGlzLmF0dHJpYnV0ZXMpIHtcbiAgICAgIHRocm93IG5ldyBFcnJvcihcbiAgICAgICAgJ0Nhbm5vdCBhZGQgJyArIHR5cGUgKyBcIiAnXCIgKyBuYW1lICsgXCInOiBhbiBhdHRyaWJ1dGUgd2l0aCB0aGF0IG5hbWUgYWxyZWFkeSBleGlzdHNcIlxuICAgICAgKTtcbiAgICB9XG4gIH1cblxuICAvLyBSZXR1cm5zIGEgd3JhcHBlciBmb3IgdGhlIGdpdmVuIENTVCBgbm9kZWAgaW4gdGhpcyBzZW1hbnRpY3MuXG4gIC8vIElmIGBub2RlYCBpcyBhbHJlYWR5IGEgd3JhcHBlciwgcmV0dXJucyBgbm9kZWAgaXRzZWxmLiAgLy8gVE9ETzogd2h5IGlzIHRoaXMgbmVlZGVkP1xuICB3cmFwKG5vZGUsIHNvdXJjZSwgb3B0QmFzZUludGVydmFsKSB7XG4gICAgY29uc3QgYmFzZUludGVydmFsID0gb3B0QmFzZUludGVydmFsIHx8IHNvdXJjZTtcbiAgICByZXR1cm4gbm9kZSBpbnN0YW5jZW9mIHRoaXMuV3JhcHBlciA/IG5vZGUgOiBuZXcgdGhpcy5XcmFwcGVyKG5vZGUsIHNvdXJjZSwgYmFzZUludGVydmFsKTtcbiAgfVxufVxuXG5mdW5jdGlvbiBwYXJzZVNpZ25hdHVyZShzaWduYXR1cmUsIHR5cGUpIHtcbiAgaWYgKCFTZW1hbnRpY3MucHJvdG90eXBlR3JhbW1hcikge1xuICAgIC8vIFRoZSBPcGVyYXRpb25zIGFuZCBBdHRyaWJ1dGVzIGdyYW1tYXIgd29uJ3QgYmUgYXZhaWxhYmxlIHdoaWxlIE9obSBpcyBsb2FkaW5nLFxuICAgIC8vIGJ1dCB3ZSBjYW4gZ2V0IGF3YXkgdGhlIGZvbGxvd2luZyBzaW1wbGlmaWNhdGlvbiBiL2Mgbm9uZSBvZiB0aGUgb3BlcmF0aW9uc1xuICAgIC8vIHRoYXQgYXJlIHVzZWQgd2hpbGUgbG9hZGluZyB0YWtlIGFyZ3VtZW50cy5cbiAgICBjb21tb24uYXNzZXJ0KHNpZ25hdHVyZS5pbmRleE9mKCcoJykgPT09IC0xKTtcbiAgICByZXR1cm4ge1xuICAgICAgbmFtZTogc2lnbmF0dXJlLFxuICAgICAgZm9ybWFsczogW10sXG4gICAgfTtcbiAgfVxuXG4gIGNvbnN0IHIgPSBTZW1hbnRpY3MucHJvdG90eXBlR3JhbW1hci5tYXRjaChcbiAgICBzaWduYXR1cmUsXG4gICAgdHlwZSA9PT0gJ29wZXJhdGlvbicgPyAnT3BlcmF0aW9uU2lnbmF0dXJlJyA6ICdBdHRyaWJ1dGVTaWduYXR1cmUnXG4gICk7XG4gIGlmIChyLmZhaWxlZCgpKSB7XG4gICAgdGhyb3cgbmV3IEVycm9yKHIubWVzc2FnZSk7XG4gIH1cblxuICByZXR1cm4gU2VtYW50aWNzLnByb3RvdHlwZUdyYW1tYXJTZW1hbnRpY3MocikucGFyc2UoKTtcbn1cblxuZnVuY3Rpb24gbmV3RGVmYXVsdEFjdGlvbih0eXBlLCBuYW1lLCBkb0l0KSB7XG4gIHJldHVybiBmdW5jdGlvbiAoLi4uY2hpbGRyZW4pIHtcbiAgICBjb25zdCB0aGlzVGhpbmcgPSB0aGlzLl9zZW1hbnRpY3Mub3BlcmF0aW9uc1tuYW1lXSB8fCB0aGlzLl9zZW1hbnRpY3MuYXR0cmlidXRlc1tuYW1lXTtcbiAgICBjb25zdCBhcmdzID0gdGhpc1RoaW5nLmZvcm1hbHMubWFwKGZvcm1hbCA9PiB0aGlzLmFyZ3NbZm9ybWFsXSk7XG5cbiAgICBpZiAoIXRoaXMuaXNJdGVyYXRpb24oKSAmJiBjaGlsZHJlbi5sZW5ndGggPT09IDEpIHtcbiAgICAgIC8vIFRoaXMgQ1NUIG5vZGUgY29ycmVzcG9uZHMgdG8gYSBub24tdGVybWluYWwgaW4gdGhlIGdyYW1tYXIgKGUuZy4sIEFkZEV4cHIpLiBUaGUgZmFjdCB0aGF0XG4gICAgICAvLyB3ZSBnb3QgaGVyZSBtZWFucyB0aGF0IHRoaXMgYWN0aW9uIGRpY3Rpb25hcnkgZG9lc24ndCBoYXZlIGFuIGFjdGlvbiBmb3IgdGhpcyBwYXJ0aWN1bGFyXG4gICAgICAvLyBub24tdGVybWluYWwgb3IgYSBnZW5lcmljIGBfbm9udGVybWluYWxgIGFjdGlvbi5cbiAgICAgIC8vIEFzIGEgY29udmVuaWVuY2UsIGlmIHRoaXMgbm9kZSBvbmx5IGhhcyBvbmUgY2hpbGQsIHdlIGp1c3QgcmV0dXJuIHRoZSByZXN1bHQgb2YgYXBwbHlpbmdcbiAgICAgIC8vIHRoaXMgb3BlcmF0aW9uIC8gYXR0cmlidXRlIHRvIHRoZSBjaGlsZCBub2RlLlxuICAgICAgcmV0dXJuIGRvSXQuYXBwbHkoY2hpbGRyZW5bMF0sIGFyZ3MpO1xuICAgIH0gZWxzZSB7XG4gICAgICAvLyBPdGhlcndpc2UsIHdlIHRocm93IGFuIGV4Y2VwdGlvbiB0byBsZXQgdGhlIHByb2dyYW1tZXIga25vdyB0aGF0IHdlIGRvbid0IGtub3cgd2hhdFxuICAgICAgLy8gdG8gZG8gd2l0aCB0aGlzIG5vZGUuXG4gICAgICB0aHJvdyBlcnJvcnMubWlzc2luZ1NlbWFudGljQWN0aW9uKHRoaXMuY3Rvck5hbWUsIG5hbWUsIHR5cGUsIGdsb2JhbEFjdGlvblN0YWNrKTtcbiAgICB9XG4gIH07XG59XG5cbi8vIENyZWF0ZXMgYSBuZXcgU2VtYW50aWNzIGluc3RhbmNlIGZvciBgZ3JhbW1hcmAsIGluaGVyaXRpbmcgb3BlcmF0aW9ucyBhbmQgYXR0cmlidXRlcyBmcm9tXG4vLyBgb3B0U3VwZXJTZW1hbnRpY3NgLCBpZiBpdCBpcyBzcGVjaWZpZWQuIFJldHVybnMgYSBmdW5jdGlvbiB0aGF0IGFjdHMgYXMgYSBwcm94eSBmb3IgdGhlIG5ld1xuLy8gU2VtYW50aWNzIGluc3RhbmNlLiBXaGVuIHRoYXQgZnVuY3Rpb24gaXMgaW52b2tlZCB3aXRoIGEgQ1NUIG5vZGUgYXMgYW4gYXJndW1lbnQsIGl0IHJldHVybnNcbi8vIGEgd3JhcHBlciBmb3IgdGhhdCBub2RlIHdoaWNoIGdpdmVzIGFjY2VzcyB0byB0aGUgb3BlcmF0aW9ucyBhbmQgYXR0cmlidXRlcyBwcm92aWRlZCBieSB0aGlzXG4vLyBzZW1hbnRpY3MuXG5TZW1hbnRpY3MuY3JlYXRlU2VtYW50aWNzID0gZnVuY3Rpb24gKGdyYW1tYXIsIG9wdFN1cGVyU2VtYW50aWNzKSB7XG4gIGNvbnN0IHMgPSBuZXcgU2VtYW50aWNzKFxuICAgIGdyYW1tYXIsXG4gICAgb3B0U3VwZXJTZW1hbnRpY3MgIT09IHVuZGVmaW5lZFxuICAgICAgPyBvcHRTdXBlclNlbWFudGljc1xuICAgICAgOiBTZW1hbnRpY3MuQnVpbHRJblNlbWFudGljcy5fZ2V0U2VtYW50aWNzKClcbiAgKTtcblxuICAvLyBUbyBlbmFibGUgY2xpZW50cyB0byBpbnZva2UgYSBzZW1hbnRpY3MgbGlrZSBhIGZ1bmN0aW9uLCByZXR1cm4gYSBmdW5jdGlvbiB0aGF0IGFjdHMgYXMgYSBwcm94eVxuICAvLyBmb3IgYHNgLCB3aGljaCBpcyB0aGUgcmVhbCBgU2VtYW50aWNzYCBpbnN0YW5jZS5cbiAgY29uc3QgcHJveHkgPSBmdW5jdGlvbiBBU2VtYW50aWNzKG1hdGNoUmVzdWx0KSB7XG4gICAgaWYgKCEobWF0Y2hSZXN1bHQgaW5zdGFuY2VvZiBNYXRjaFJlc3VsdCkpIHtcbiAgICAgIHRocm93IG5ldyBUeXBlRXJyb3IoXG4gICAgICAgICdTZW1hbnRpY3MgZXhwZWN0ZWQgYSBNYXRjaFJlc3VsdCwgYnV0IGdvdCAnICtcbiAgICAgICAgICBjb21tb24udW5leHBlY3RlZE9ialRvU3RyaW5nKG1hdGNoUmVzdWx0KVxuICAgICAgKTtcbiAgICB9XG4gICAgaWYgKG1hdGNoUmVzdWx0LmZhaWxlZCgpKSB7XG4gICAgICB0aHJvdyBuZXcgVHlwZUVycm9yKCdjYW5ub3QgYXBwbHkgU2VtYW50aWNzIHRvICcgKyBtYXRjaFJlc3VsdC50b1N0cmluZygpKTtcbiAgICB9XG5cbiAgICBjb25zdCBjc3QgPSBtYXRjaFJlc3VsdC5fY3N0O1xuICAgIGlmIChjc3QuZ3JhbW1hciAhPT0gZ3JhbW1hcikge1xuICAgICAgdGhyb3cgbmV3IEVycm9yKFxuICAgICAgICBcIkNhbm5vdCB1c2UgYSBNYXRjaFJlc3VsdCBmcm9tIGdyYW1tYXIgJ1wiICtcbiAgICAgICAgICBjc3QuZ3JhbW1hci5uYW1lICtcbiAgICAgICAgICBcIicgd2l0aCBhIHNlbWFudGljcyBmb3IgJ1wiICtcbiAgICAgICAgICBncmFtbWFyLm5hbWUgK1xuICAgICAgICAgIFwiJ1wiXG4gICAgICApO1xuICAgIH1cbiAgICBjb25zdCBpbnB1dFN0cmVhbSA9IG5ldyBJbnB1dFN0cmVhbShtYXRjaFJlc3VsdC5pbnB1dCk7XG4gICAgcmV0dXJuIHMud3JhcChjc3QsIGlucHV0U3RyZWFtLmludGVydmFsKG1hdGNoUmVzdWx0Ll9jc3RPZmZzZXQsIG1hdGNoUmVzdWx0LmlucHV0Lmxlbmd0aCkpO1xuICB9O1xuXG4gIC8vIEZvcndhcmQgcHVibGljIG1ldGhvZHMgZnJvbSB0aGUgcHJveHkgdG8gdGhlIHNlbWFudGljcyBpbnN0YW5jZS5cbiAgcHJveHkuYWRkT3BlcmF0aW9uID0gZnVuY3Rpb24gKHNpZ25hdHVyZSwgYWN0aW9uRGljdCkge1xuICAgIHMuYWRkT3BlcmF0aW9uT3JBdHRyaWJ1dGUoJ29wZXJhdGlvbicsIHNpZ25hdHVyZSwgYWN0aW9uRGljdCk7XG4gICAgcmV0dXJuIHByb3h5O1xuICB9O1xuICBwcm94eS5leHRlbmRPcGVyYXRpb24gPSBmdW5jdGlvbiAobmFtZSwgYWN0aW9uRGljdCkge1xuICAgIHMuZXh0ZW5kT3BlcmF0aW9uT3JBdHRyaWJ1dGUoJ29wZXJhdGlvbicsIG5hbWUsIGFjdGlvbkRpY3QpO1xuICAgIHJldHVybiBwcm94eTtcbiAgfTtcbiAgcHJveHkuYWRkQXR0cmlidXRlID0gZnVuY3Rpb24gKG5hbWUsIGFjdGlvbkRpY3QpIHtcbiAgICBzLmFkZE9wZXJhdGlvbk9yQXR0cmlidXRlKCdhdHRyaWJ1dGUnLCBuYW1lLCBhY3Rpb25EaWN0KTtcbiAgICByZXR1cm4gcHJveHk7XG4gIH07XG4gIHByb3h5LmV4dGVuZEF0dHJpYnV0ZSA9IGZ1bmN0aW9uIChuYW1lLCBhY3Rpb25EaWN0KSB7XG4gICAgcy5leHRlbmRPcGVyYXRpb25PckF0dHJpYnV0ZSgnYXR0cmlidXRlJywgbmFtZSwgYWN0aW9uRGljdCk7XG4gICAgcmV0dXJuIHByb3h5O1xuICB9O1xuICBwcm94eS5fZ2V0QWN0aW9uRGljdCA9IGZ1bmN0aW9uIChvcGVyYXRpb25PckF0dHJpYnV0ZU5hbWUpIHtcbiAgICBjb25zdCBhY3Rpb24gPVxuICAgICAgcy5vcGVyYXRpb25zW29wZXJhdGlvbk9yQXR0cmlidXRlTmFtZV0gfHwgcy5hdHRyaWJ1dGVzW29wZXJhdGlvbk9yQXR0cmlidXRlTmFtZV07XG4gICAgaWYgKCFhY3Rpb24pIHtcbiAgICAgIHRocm93IG5ldyBFcnJvcihcbiAgICAgICAgJ1wiJyArXG4gICAgICAgICAgb3BlcmF0aW9uT3JBdHRyaWJ1dGVOYW1lICtcbiAgICAgICAgICAnXCIgaXMgbm90IGEgdmFsaWQgb3BlcmF0aW9uIG9yIGF0dHJpYnV0ZSAnICtcbiAgICAgICAgICAnbmFtZSBpbiB0aGlzIHNlbWFudGljcyBmb3IgXCInICtcbiAgICAgICAgICBncmFtbWFyLm5hbWUgK1xuICAgICAgICAgICdcIidcbiAgICAgICk7XG4gICAgfVxuICAgIHJldHVybiBhY3Rpb24uYWN0aW9uRGljdDtcbiAgfTtcbiAgcHJveHkuX3JlbW92ZSA9IGZ1bmN0aW9uIChvcGVyYXRpb25PckF0dHJpYnV0ZU5hbWUpIHtcbiAgICBsZXQgc2VtYW50aWM7XG4gICAgaWYgKG9wZXJhdGlvbk9yQXR0cmlidXRlTmFtZSBpbiBzLm9wZXJhdGlvbnMpIHtcbiAgICAgIHNlbWFudGljID0gcy5vcGVyYXRpb25zW29wZXJhdGlvbk9yQXR0cmlidXRlTmFtZV07XG4gICAgICBkZWxldGUgcy5vcGVyYXRpb25zW29wZXJhdGlvbk9yQXR0cmlidXRlTmFtZV07XG4gICAgfSBlbHNlIGlmIChvcGVyYXRpb25PckF0dHJpYnV0ZU5hbWUgaW4gcy5hdHRyaWJ1dGVzKSB7XG4gICAgICBzZW1hbnRpYyA9IHMuYXR0cmlidXRlc1tvcGVyYXRpb25PckF0dHJpYnV0ZU5hbWVdO1xuICAgICAgZGVsZXRlIHMuYXR0cmlidXRlc1tvcGVyYXRpb25PckF0dHJpYnV0ZU5hbWVdO1xuICAgIH1cbiAgICBkZWxldGUgcy5XcmFwcGVyLnByb3RvdHlwZVtvcGVyYXRpb25PckF0dHJpYnV0ZU5hbWVdO1xuICAgIHJldHVybiBzZW1hbnRpYztcbiAgfTtcbiAgcHJveHkuZ2V0T3BlcmF0aW9uTmFtZXMgPSBmdW5jdGlvbiAoKSB7XG4gICAgcmV0dXJuIE9iamVjdC5rZXlzKHMub3BlcmF0aW9ucyk7XG4gIH07XG4gIHByb3h5LmdldEF0dHJpYnV0ZU5hbWVzID0gZnVuY3Rpb24gKCkge1xuICAgIHJldHVybiBPYmplY3Qua2V5cyhzLmF0dHJpYnV0ZXMpO1xuICB9O1xuICBwcm94eS5nZXRHcmFtbWFyID0gZnVuY3Rpb24gKCkge1xuICAgIHJldHVybiBzLmdyYW1tYXI7XG4gIH07XG4gIHByb3h5LnRvUmVjaXBlID0gZnVuY3Rpb24gKHNlbWFudGljc09ubHkpIHtcbiAgICByZXR1cm4gcy50b1JlY2lwZShzZW1hbnRpY3NPbmx5KTtcbiAgfTtcblxuICAvLyBNYWtlIHRoZSBwcm94eSdzIHRvU3RyaW5nKCkgd29yay5cbiAgcHJveHkudG9TdHJpbmcgPSBzLnRvU3RyaW5nLmJpbmQocyk7XG5cbiAgLy8gUmV0dXJucyB0aGUgc2VtYW50aWNzIGZvciB0aGUgcHJveHkuXG4gIHByb3h5Ll9nZXRTZW1hbnRpY3MgPSBmdW5jdGlvbiAoKSB7XG4gICAgcmV0dXJuIHM7XG4gIH07XG5cbiAgcmV0dXJuIHByb3h5O1xufTtcblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0gT3BlcmF0aW9uIC0tLS0tLS0tLS0tLS0tLS0tXG5cbi8vIEFuIE9wZXJhdGlvbiByZXByZXNlbnRzIGEgZnVuY3Rpb24gdG8gYmUgYXBwbGllZCB0byBhIGNvbmNyZXRlIHN5bnRheCB0cmVlIChDU1QpIC0tIGl0J3MgdmVyeVxuLy8gc2ltaWxhciB0byBhIFZpc2l0b3IgKGh0dHA6Ly9lbi53aWtpcGVkaWEub3JnL3dpa2kvVmlzaXRvcl9wYXR0ZXJuKS4gQW4gb3BlcmF0aW9uIGlzIGV4ZWN1dGVkIGJ5XG4vLyByZWN1cnNpdmVseSB3YWxraW5nIHRoZSBDU1QsIGFuZCBhdCBlYWNoIG5vZGUsIGludm9raW5nIHRoZSBtYXRjaGluZyBzZW1hbnRpYyBhY3Rpb24gZnJvbVxuLy8gYGFjdGlvbkRpY3RgLiBTZWUgYE9wZXJhdGlvbi5wcm90b3R5cGUuZXhlY3V0ZWAgZm9yIGRldGFpbHMgb2YgaG93IGEgQ1NUIG5vZGUncyBtYXRjaGluZyBzZW1hbnRpY1xuLy8gYWN0aW9uIGlzIGZvdW5kLlxuY2xhc3MgT3BlcmF0aW9uIHtcbiAgY29uc3RydWN0b3IobmFtZSwgZm9ybWFscywgYWN0aW9uRGljdCwgYnVpbHRJbkRlZmF1bHQpIHtcbiAgICB0aGlzLm5hbWUgPSBuYW1lO1xuICAgIHRoaXMuZm9ybWFscyA9IGZvcm1hbHM7XG4gICAgdGhpcy5hY3Rpb25EaWN0ID0gYWN0aW9uRGljdDtcbiAgICB0aGlzLmJ1aWx0SW5EZWZhdWx0ID0gYnVpbHRJbkRlZmF1bHQ7XG4gIH1cblxuICBjaGVja0FjdGlvbkRpY3QoZ3JhbW1hcikge1xuICAgIGdyYW1tYXIuX2NoZWNrVG9wRG93bkFjdGlvbkRpY3QodGhpcy50eXBlTmFtZSwgdGhpcy5uYW1lLCB0aGlzLmFjdGlvbkRpY3QpO1xuICB9XG5cbiAgLy8gRXhlY3V0ZSB0aGlzIG9wZXJhdGlvbiBvbiB0aGUgQ1NUIG5vZGUgYXNzb2NpYXRlZCB3aXRoIGBub2RlV3JhcHBlcmAgaW4gdGhlIGNvbnRleHQgb2YgdGhlXG4gIC8vIGdpdmVuIFNlbWFudGljcyBpbnN0YW5jZS5cbiAgZXhlY3V0ZShzZW1hbnRpY3MsIG5vZGVXcmFwcGVyKSB7XG4gICAgdHJ5IHtcbiAgICAgIC8vIExvb2sgZm9yIGEgc2VtYW50aWMgYWN0aW9uIHdob3NlIG5hbWUgbWF0Y2hlcyB0aGUgbm9kZSdzIGNvbnN0cnVjdG9yIG5hbWUsIHdoaWNoIGlzIGVpdGhlclxuICAgICAgLy8gdGhlIG5hbWUgb2YgYSBydWxlIGluIHRoZSBncmFtbWFyLCBvciAnX3Rlcm1pbmFsJyAoZm9yIGEgdGVybWluYWwgbm9kZSksIG9yICdfaXRlcicgKGZvciBhblxuICAgICAgLy8gaXRlcmF0aW9uIG5vZGUpLlxuICAgICAgY29uc3Qge2N0b3JOYW1lfSA9IG5vZGVXcmFwcGVyLl9ub2RlO1xuICAgICAgbGV0IGFjdGlvbkZuID0gdGhpcy5hY3Rpb25EaWN0W2N0b3JOYW1lXTtcbiAgICAgIGlmIChhY3Rpb25Gbikge1xuICAgICAgICBnbG9iYWxBY3Rpb25TdGFjay5wdXNoKFt0aGlzLCBjdG9yTmFtZV0pO1xuICAgICAgICByZXR1cm4gYWN0aW9uRm4uYXBwbHkobm9kZVdyYXBwZXIsIG5vZGVXcmFwcGVyLl9jaGlsZHJlbigpKTtcbiAgICAgIH1cblxuICAgICAgLy8gVGhlIGFjdGlvbiBkaWN0aW9uYXJ5IGRvZXMgbm90IGNvbnRhaW4gYSBzZW1hbnRpYyBhY3Rpb24gZm9yIHRoaXMgc3BlY2lmaWMgdHlwZSBvZiBub2RlLlxuICAgICAgLy8gSWYgdGhpcyBpcyBhIG5vbnRlcm1pbmFsIG5vZGUgYW5kIHRoZSBwcm9ncmFtbWVyIGhhcyBwcm92aWRlZCBhIGBfbm9udGVybWluYWxgIHNlbWFudGljXG4gICAgICAvLyBhY3Rpb24sIHdlIGludm9rZSBpdDpcbiAgICAgIGlmIChub2RlV3JhcHBlci5pc05vbnRlcm1pbmFsKCkpIHtcbiAgICAgICAgYWN0aW9uRm4gPSB0aGlzLmFjdGlvbkRpY3QuX25vbnRlcm1pbmFsO1xuICAgICAgICBpZiAoYWN0aW9uRm4pIHtcbiAgICAgICAgICBnbG9iYWxBY3Rpb25TdGFjay5wdXNoKFt0aGlzLCAnX25vbnRlcm1pbmFsJywgY3Rvck5hbWVdKTtcbiAgICAgICAgICByZXR1cm4gYWN0aW9uRm4uYXBwbHkobm9kZVdyYXBwZXIsIG5vZGVXcmFwcGVyLl9jaGlsZHJlbigpKTtcbiAgICAgICAgfVxuICAgICAgfVxuXG4gICAgICAvLyBPdGhlcndpc2UsIHdlIGludm9rZSB0aGUgJ19kZWZhdWx0JyBzZW1hbnRpYyBhY3Rpb24uXG4gICAgICBnbG9iYWxBY3Rpb25TdGFjay5wdXNoKFt0aGlzLCAnZGVmYXVsdCBhY3Rpb24nLCBjdG9yTmFtZV0pO1xuICAgICAgcmV0dXJuIHRoaXMuYWN0aW9uRGljdC5fZGVmYXVsdC5hcHBseShub2RlV3JhcHBlciwgbm9kZVdyYXBwZXIuX2NoaWxkcmVuKCkpO1xuICAgIH0gZmluYWxseSB7XG4gICAgICBnbG9iYWxBY3Rpb25TdGFjay5wb3AoKTtcbiAgICB9XG4gIH1cbn1cblxuT3BlcmF0aW9uLnByb3RvdHlwZS50eXBlTmFtZSA9ICdvcGVyYXRpb24nO1xuXG4vLyAtLS0tLS0tLS0tLS0tLS0tLSBBdHRyaWJ1dGUgLS0tLS0tLS0tLS0tLS0tLS1cblxuLy8gQXR0cmlidXRlcyBhcmUgT3BlcmF0aW9ucyB3aG9zZSByZXN1bHRzIGFyZSBtZW1vaXplZC4gVGhpcyBtZWFucyB0aGF0LCBmb3IgYW55IGdpdmVuIHNlbWFudGljcyxcbi8vIHRoZSBzZW1hbnRpYyBhY3Rpb24gZm9yIGEgQ1NUIG5vZGUgd2lsbCBiZSBpbnZva2VkIG5vIG1vcmUgdGhhbiBvbmNlLlxuY2xhc3MgQXR0cmlidXRlIGV4dGVuZHMgT3BlcmF0aW9uIHtcbiAgY29uc3RydWN0b3IobmFtZSwgYWN0aW9uRGljdCwgYnVpbHRJbkRlZmF1bHQpIHtcbiAgICBzdXBlcihuYW1lLCBbXSwgYWN0aW9uRGljdCwgYnVpbHRJbkRlZmF1bHQpO1xuICB9XG5cbiAgZXhlY3V0ZShzZW1hbnRpY3MsIG5vZGVXcmFwcGVyKSB7XG4gICAgY29uc3Qgbm9kZSA9IG5vZGVXcmFwcGVyLl9ub2RlO1xuICAgIGNvbnN0IGtleSA9IHNlbWFudGljcy5hdHRyaWJ1dGVLZXlzW3RoaXMubmFtZV07XG4gICAgaWYgKCFoYXNPd25Qcm9wZXJ0eShub2RlLCBrZXkpKSB7XG4gICAgICAvLyBUaGUgZm9sbG93aW5nIGlzIGEgc3VwZXItc2VuZCAtLSBpc24ndCBKUyBiZWF1dGlmdWw/IDovXG4gICAgICBub2RlW2tleV0gPSBPcGVyYXRpb24ucHJvdG90eXBlLmV4ZWN1dGUuY2FsbCh0aGlzLCBzZW1hbnRpY3MsIG5vZGVXcmFwcGVyKTtcbiAgICB9XG4gICAgcmV0dXJuIG5vZGVba2V5XTtcbiAgfVxufVxuXG5BdHRyaWJ1dGUucHJvdG90eXBlLnR5cGVOYW1lID0gJ2F0dHJpYnV0ZSc7XG4iLCJpbXBvcnQge01hdGNoZXJ9IGZyb20gJy4vTWF0Y2hlci5qcyc7XG5pbXBvcnQge1NlbWFudGljc30gZnJvbSAnLi9TZW1hbnRpY3MuanMnO1xuaW1wb3J0ICogYXMgY29tbW9uIGZyb20gJy4vY29tbW9uLmpzJztcbmltcG9ydCAqIGFzIGVycm9ycyBmcm9tICcuL2Vycm9ycy5qcyc7XG5pbXBvcnQgKiBhcyBwZXhwcnMgZnJvbSAnLi9wZXhwcnMuanMnO1xuXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gUHJpdmF0ZSBzdHVmZlxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cblxuY29uc3QgU1BFQ0lBTF9BQ1RJT05fTkFNRVMgPSBbJ19pdGVyJywgJ190ZXJtaW5hbCcsICdfbm9udGVybWluYWwnLCAnX2RlZmF1bHQnXTtcblxuZnVuY3Rpb24gZ2V0U29ydGVkUnVsZVZhbHVlcyhncmFtbWFyKSB7XG4gIHJldHVybiBPYmplY3Qua2V5cyhncmFtbWFyLnJ1bGVzKVxuICAgIC5zb3J0KClcbiAgICAubWFwKG5hbWUgPT4gZ3JhbW1hci5ydWxlc1tuYW1lXSk7XG59XG5cbi8vIFVudGlsIEVTMjAxOSwgSlNPTiB3YXMgbm90IGEgdmFsaWQgc3Vic2V0IG9mIEphdmFTY3JpcHQgYmVjYXVzZSBVKzIwMjggKGxpbmUgc2VwYXJhdG9yKVxuLy8gYW5kIFUrMjAyOSAocGFyYWdyYXBoIHNlcGFyYXRvcikgYXJlIGFsbG93ZWQgaW4gSlNPTiBzdHJpbmcgbGl0ZXJhbHMsIGJ1dCBub3QgaW4gSlMuXG4vLyBUaGlzIGZ1bmN0aW9uIHByb3Blcmx5IGVuY29kZXMgdGhvc2UgdHdvIGNoYXJhY3RlcnMgc28gdGhhdCB0aGUgcmVzdWx0aW5nIHN0cmluZyBpc1xuLy8gcmVwcmVzZW50cyBib3RoIHZhbGlkIEpTT04sIGFuZCB2YWxpZCBKYXZhU2NyaXB0IChmb3IgRVMyMDE4IGFuZCBiZWxvdykuXG4vLyBTZWUgaHR0cHM6Ly92OC5kZXYvZmVhdHVyZXMvc3Vic3VtZS1qc29uIGZvciBtb3JlIGRldGFpbHMuXG5jb25zdCBqc29uVG9KUyA9IHN0ciA9PiBzdHIucmVwbGFjZSgvXFx1MjAyOC9nLCAnXFxcXHUyMDI4JykucmVwbGFjZSgvXFx1MjAyOS9nLCAnXFxcXHUyMDI5Jyk7XG5cbmxldCBvaG1HcmFtbWFyO1xubGV0IGJ1aWxkR3JhbW1hcjtcblxuZXhwb3J0IGNsYXNzIEdyYW1tYXIge1xuICBjb25zdHJ1Y3RvcihuYW1lLCBzdXBlckdyYW1tYXIsIHJ1bGVzLCBvcHREZWZhdWx0U3RhcnRSdWxlKSB7XG4gICAgdGhpcy5uYW1lID0gbmFtZTtcbiAgICB0aGlzLnN1cGVyR3JhbW1hciA9IHN1cGVyR3JhbW1hcjtcbiAgICB0aGlzLnJ1bGVzID0gcnVsZXM7XG4gICAgaWYgKG9wdERlZmF1bHRTdGFydFJ1bGUpIHtcbiAgICAgIGlmICghKG9wdERlZmF1bHRTdGFydFJ1bGUgaW4gcnVsZXMpKSB7XG4gICAgICAgIHRocm93IG5ldyBFcnJvcihcbiAgICAgICAgICBcIkludmFsaWQgc3RhcnQgcnVsZTogJ1wiICtcbiAgICAgICAgICAgIG9wdERlZmF1bHRTdGFydFJ1bGUgK1xuICAgICAgICAgICAgXCInIGlzIG5vdCBhIHJ1bGUgaW4gZ3JhbW1hciAnXCIgK1xuICAgICAgICAgICAgbmFtZSArXG4gICAgICAgICAgICBcIidcIlxuICAgICAgICApO1xuICAgICAgfVxuICAgICAgdGhpcy5kZWZhdWx0U3RhcnRSdWxlID0gb3B0RGVmYXVsdFN0YXJ0UnVsZTtcbiAgICB9XG4gICAgdGhpcy5fbWF0Y2hTdGF0ZUluaXRpYWxpemVyID0gdW5kZWZpbmVkO1xuICAgIHRoaXMuc3VwcG9ydHNJbmNyZW1lbnRhbFBhcnNpbmcgPSB0cnVlO1xuICB9XG5cbiAgbWF0Y2hlcigpIHtcbiAgICByZXR1cm4gbmV3IE1hdGNoZXIodGhpcyk7XG4gIH1cblxuICAvLyBSZXR1cm4gdHJ1ZSBpZiB0aGUgZ3JhbW1hciBpcyBhIGJ1aWx0LWluIGdyYW1tYXIsIG90aGVyd2lzZSBmYWxzZS5cbiAgLy8gTk9URTogVGhpcyBtaWdodCBnaXZlIGFuIHVuZXhwZWN0ZWQgcmVzdWx0IGlmIGNhbGxlZCBiZWZvcmUgQnVpbHRJblJ1bGVzIGlzIGRlZmluZWQhXG4gIGlzQnVpbHRJbigpIHtcbiAgICByZXR1cm4gdGhpcyA9PT0gR3JhbW1hci5Qcm90b0J1aWx0SW5SdWxlcyB8fCB0aGlzID09PSBHcmFtbWFyLkJ1aWx0SW5SdWxlcztcbiAgfVxuXG4gIGVxdWFscyhnKSB7XG4gICAgaWYgKHRoaXMgPT09IGcpIHtcbiAgICAgIHJldHVybiB0cnVlO1xuICAgIH1cbiAgICAvLyBEbyB0aGUgY2hlYXBlc3QgY29tcGFyaXNvbnMgZmlyc3QuXG4gICAgaWYgKFxuICAgICAgZyA9PSBudWxsIHx8XG4gICAgICB0aGlzLm5hbWUgIT09IGcubmFtZSB8fFxuICAgICAgdGhpcy5kZWZhdWx0U3RhcnRSdWxlICE9PSBnLmRlZmF1bHRTdGFydFJ1bGUgfHxcbiAgICAgICEodGhpcy5zdXBlckdyYW1tYXIgPT09IGcuc3VwZXJHcmFtbWFyIHx8IHRoaXMuc3VwZXJHcmFtbWFyLmVxdWFscyhnLnN1cGVyR3JhbW1hcikpXG4gICAgKSB7XG4gICAgICByZXR1cm4gZmFsc2U7XG4gICAgfVxuICAgIGNvbnN0IG15UnVsZXMgPSBnZXRTb3J0ZWRSdWxlVmFsdWVzKHRoaXMpO1xuICAgIGNvbnN0IG90aGVyUnVsZXMgPSBnZXRTb3J0ZWRSdWxlVmFsdWVzKGcpO1xuICAgIHJldHVybiAoXG4gICAgICBteVJ1bGVzLmxlbmd0aCA9PT0gb3RoZXJSdWxlcy5sZW5ndGggJiZcbiAgICAgIG15UnVsZXMuZXZlcnkoKHJ1bGUsIGkpID0+IHtcbiAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICBydWxlLmRlc2NyaXB0aW9uID09PSBvdGhlclJ1bGVzW2ldLmRlc2NyaXB0aW9uICYmXG4gICAgICAgICAgcnVsZS5mb3JtYWxzLmpvaW4oJywnKSA9PT0gb3RoZXJSdWxlc1tpXS5mb3JtYWxzLmpvaW4oJywnKSAmJlxuICAgICAgICAgIHJ1bGUuYm9keS50b1N0cmluZygpID09PSBvdGhlclJ1bGVzW2ldLmJvZHkudG9TdHJpbmcoKVxuICAgICAgICApO1xuICAgICAgfSlcbiAgICApO1xuICB9XG5cbiAgbWF0Y2goaW5wdXQsIG9wdFN0YXJ0QXBwbGljYXRpb24pIHtcbiAgICBjb25zdCBtID0gdGhpcy5tYXRjaGVyKCk7XG4gICAgbS5yZXBsYWNlSW5wdXRSYW5nZSgwLCAwLCBpbnB1dCk7XG4gICAgcmV0dXJuIG0ubWF0Y2gob3B0U3RhcnRBcHBsaWNhdGlvbik7XG4gIH1cblxuICB0cmFjZShpbnB1dCwgb3B0U3RhcnRBcHBsaWNhdGlvbikge1xuICAgIGNvbnN0IG0gPSB0aGlzLm1hdGNoZXIoKTtcbiAgICBtLnJlcGxhY2VJbnB1dFJhbmdlKDAsIDAsIGlucHV0KTtcbiAgICByZXR1cm4gbS50cmFjZShvcHRTdGFydEFwcGxpY2F0aW9uKTtcbiAgfVxuXG4gIGNyZWF0ZVNlbWFudGljcygpIHtcbiAgICByZXR1cm4gU2VtYW50aWNzLmNyZWF0ZVNlbWFudGljcyh0aGlzKTtcbiAgfVxuXG4gIGV4dGVuZFNlbWFudGljcyhzdXBlclNlbWFudGljcykge1xuICAgIHJldHVybiBTZW1hbnRpY3MuY3JlYXRlU2VtYW50aWNzKHRoaXMsIHN1cGVyU2VtYW50aWNzLl9nZXRTZW1hbnRpY3MoKSk7XG4gIH1cblxuICAvLyBDaGVjayB0aGF0IGV2ZXJ5IGtleSBpbiBgYWN0aW9uRGljdGAgY29ycmVzcG9uZHMgdG8gYSBzZW1hbnRpYyBhY3Rpb24sIGFuZCB0aGF0IGl0IG1hcHMgdG9cbiAgLy8gYSBmdW5jdGlvbiBvZiB0aGUgY29ycmVjdCBhcml0eS4gSWYgbm90LCB0aHJvdyBhbiBleGNlcHRpb24uXG4gIF9jaGVja1RvcERvd25BY3Rpb25EaWN0KHdoYXQsIG5hbWUsIGFjdGlvbkRpY3QpIHtcbiAgICBjb25zdCBwcm9ibGVtcyA9IFtdO1xuXG4gICAgZm9yIChjb25zdCBrIGluIGFjdGlvbkRpY3QpIHtcbiAgICAgIGNvbnN0IHYgPSBhY3Rpb25EaWN0W2tdO1xuICAgICAgY29uc3QgaXNTcGVjaWFsQWN0aW9uID0gU1BFQ0lBTF9BQ1RJT05fTkFNRVMuaW5jbHVkZXMoayk7XG5cbiAgICAgIGlmICghaXNTcGVjaWFsQWN0aW9uICYmICEoayBpbiB0aGlzLnJ1bGVzKSkge1xuICAgICAgICBwcm9ibGVtcy5wdXNoKGAnJHtrfScgaXMgbm90IGEgdmFsaWQgc2VtYW50aWMgYWN0aW9uIGZvciAnJHt0aGlzLm5hbWV9J2ApO1xuICAgICAgICBjb250aW51ZTtcbiAgICAgIH1cbiAgICAgIGlmICh0eXBlb2YgdiAhPT0gJ2Z1bmN0aW9uJykge1xuICAgICAgICBwcm9ibGVtcy5wdXNoKGAnJHtrfScgbXVzdCBiZSBhIGZ1bmN0aW9uIGluIGFuIGFjdGlvbiBkaWN0aW9uYXJ5IGZvciAnJHt0aGlzLm5hbWV9J2ApO1xuICAgICAgICBjb250aW51ZTtcbiAgICAgIH1cbiAgICAgIGNvbnN0IGFjdHVhbCA9IHYubGVuZ3RoO1xuICAgICAgY29uc3QgZXhwZWN0ZWQgPSB0aGlzLl90b3BEb3duQWN0aW9uQXJpdHkoayk7XG4gICAgICBpZiAoYWN0dWFsICE9PSBleHBlY3RlZCkge1xuICAgICAgICBsZXQgZGV0YWlscztcbiAgICAgICAgaWYgKGsgPT09ICdfaXRlcicgfHwgayA9PT0gJ19ub250ZXJtaW5hbCcpIHtcbiAgICAgICAgICBkZXRhaWxzID1cbiAgICAgICAgICAgIGBpdCBzaG91bGQgdXNlIGEgcmVzdCBwYXJhbWV0ZXIsIGUuZy4gXFxgJHtrfSguLi5jaGlsZHJlbikge31cXGAuIGAgK1xuICAgICAgICAgICAgJ05PVEU6IHRoaXMgaXMgbmV3IGluIE9obSB2MTYg4oCUIHNlZSBodHRwczovL29obWpzLm9yZy9kL2F0aSBmb3IgZGV0YWlscy4nO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIGRldGFpbHMgPSBgZXhwZWN0ZWQgJHtleHBlY3RlZH0sIGdvdCAke2FjdHVhbH1gO1xuICAgICAgICB9XG4gICAgICAgIHByb2JsZW1zLnB1c2goYFNlbWFudGljIGFjdGlvbiAnJHtrfScgaGFzIHRoZSB3cm9uZyBhcml0eTogJHtkZXRhaWxzfWApO1xuICAgICAgfVxuICAgIH1cbiAgICBpZiAocHJvYmxlbXMubGVuZ3RoID4gMCkge1xuICAgICAgY29uc3QgcHJldHR5UHJvYmxlbXMgPSBwcm9ibGVtcy5tYXAocHJvYmxlbSA9PiAnLSAnICsgcHJvYmxlbSk7XG4gICAgICBjb25zdCBlcnJvciA9IG5ldyBFcnJvcihcbiAgICAgICAgW1xuICAgICAgICAgIGBGb3VuZCBlcnJvcnMgaW4gdGhlIGFjdGlvbiBkaWN0aW9uYXJ5IG9mIHRoZSAnJHtuYW1lfScgJHt3aGF0fTpgLFxuICAgICAgICAgIC4uLnByZXR0eVByb2JsZW1zLFxuICAgICAgICBdLmpvaW4oJ1xcbicpXG4gICAgICApO1xuICAgICAgZXJyb3IucHJvYmxlbXMgPSBwcm9ibGVtcztcbiAgICAgIHRocm93IGVycm9yO1xuICAgIH1cbiAgfVxuXG4gIC8vIFJldHVybiB0aGUgZXhwZWN0ZWQgYXJpdHkgZm9yIGEgc2VtYW50aWMgYWN0aW9uIG5hbWVkIGBhY3Rpb25OYW1lYCwgd2hpY2hcbiAgLy8gaXMgZWl0aGVyIGEgcnVsZSBuYW1lIG9yIGEgc3BlY2lhbCBhY3Rpb24gbmFtZSBsaWtlICdfbm9udGVybWluYWwnLlxuICBfdG9wRG93bkFjdGlvbkFyaXR5KGFjdGlvbk5hbWUpIHtcbiAgICAvLyBBbGwgc3BlY2lhbCBhY3Rpb25zIGhhdmUgYW4gZXhwZWN0ZWQgYXJpdHkgb2YgMCwgdGhvdWdoIGFsbCBidXQgX3Rlcm1pbmFsXG4gICAgLy8gYXJlIGV4cGVjdGVkIHRvIHVzZSB0aGUgcmVzdCBwYXJhbWV0ZXIgc3ludGF4IChlLmcuIGBfaXRlciguLi5jaGlsZHJlbilgKS5cbiAgICAvLyBUaGlzIGlzIGNvbnNpZGVyZWQgdG8gaGF2ZSBhcml0eSAwLCBpLmUuIGAoKC4uLmFyZ3MpID0+IHt9KS5sZW5ndGhgIGlzIDAuXG4gICAgcmV0dXJuIFNQRUNJQUxfQUNUSU9OX05BTUVTLmluY2x1ZGVzKGFjdGlvbk5hbWUpXG4gICAgICA/IDBcbiAgICAgIDogdGhpcy5ydWxlc1thY3Rpb25OYW1lXS5ib2R5LmdldEFyaXR5KCk7XG4gIH1cblxuICBfaW5oZXJpdHNGcm9tKGdyYW1tYXIpIHtcbiAgICBsZXQgZyA9IHRoaXMuc3VwZXJHcmFtbWFyO1xuICAgIHdoaWxlIChnKSB7XG4gICAgICBpZiAoZy5lcXVhbHMoZ3JhbW1hciwgdHJ1ZSkpIHtcbiAgICAgICAgcmV0dXJuIHRydWU7XG4gICAgICB9XG4gICAgICBnID0gZy5zdXBlckdyYW1tYXI7XG4gICAgfVxuICAgIHJldHVybiBmYWxzZTtcbiAgfVxuXG4gIHRvUmVjaXBlKHN1cGVyR3JhbW1hckV4cHIgPSB1bmRlZmluZWQpIHtcbiAgICBjb25zdCBtZXRhSW5mbyA9IHt9O1xuICAgIC8vIEluY2x1ZGUgdGhlIGdyYW1tYXIgc291cmNlIGlmIGl0IGlzIGF2YWlsYWJsZS5cbiAgICBpZiAodGhpcy5zb3VyY2UpIHtcbiAgICAgIG1ldGFJbmZvLnNvdXJjZSA9IHRoaXMuc291cmNlLmNvbnRlbnRzO1xuICAgIH1cblxuICAgIGxldCBzdGFydFJ1bGUgPSBudWxsO1xuICAgIGlmICh0aGlzLmRlZmF1bHRTdGFydFJ1bGUpIHtcbiAgICAgIHN0YXJ0UnVsZSA9IHRoaXMuZGVmYXVsdFN0YXJ0UnVsZTtcbiAgICB9XG5cbiAgICBjb25zdCBydWxlcyA9IHt9O1xuICAgIE9iamVjdC5rZXlzKHRoaXMucnVsZXMpLmZvckVhY2gocnVsZU5hbWUgPT4ge1xuICAgICAgY29uc3QgcnVsZUluZm8gPSB0aGlzLnJ1bGVzW3J1bGVOYW1lXTtcbiAgICAgIGNvbnN0IHtib2R5fSA9IHJ1bGVJbmZvO1xuICAgICAgY29uc3QgaXNEZWZpbml0aW9uID0gIXRoaXMuc3VwZXJHcmFtbWFyIHx8ICF0aGlzLnN1cGVyR3JhbW1hci5ydWxlc1tydWxlTmFtZV07XG5cbiAgICAgIGxldCBvcGVyYXRpb247XG4gICAgICBpZiAoaXNEZWZpbml0aW9uKSB7XG4gICAgICAgIG9wZXJhdGlvbiA9ICdkZWZpbmUnO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgb3BlcmF0aW9uID0gYm9keSBpbnN0YW5jZW9mIHBleHBycy5FeHRlbmQgPyAnZXh0ZW5kJyA6ICdvdmVycmlkZSc7XG4gICAgICB9XG5cbiAgICAgIGNvbnN0IG1ldGFJbmZvID0ge307XG4gICAgICBpZiAocnVsZUluZm8uc291cmNlICYmIHRoaXMuc291cmNlKSB7XG4gICAgICAgIGNvbnN0IGFkanVzdGVkID0gcnVsZUluZm8uc291cmNlLnJlbGF0aXZlVG8odGhpcy5zb3VyY2UpO1xuICAgICAgICBtZXRhSW5mby5zb3VyY2VJbnRlcnZhbCA9IFthZGp1c3RlZC5zdGFydElkeCwgYWRqdXN0ZWQuZW5kSWR4XTtcbiAgICAgIH1cblxuICAgICAgY29uc3QgZGVzY3JpcHRpb24gPSBpc0RlZmluaXRpb24gPyBydWxlSW5mby5kZXNjcmlwdGlvbiA6IG51bGw7XG4gICAgICBjb25zdCBib2R5UmVjaXBlID0gYm9keS5vdXRwdXRSZWNpcGUocnVsZUluZm8uZm9ybWFscywgdGhpcy5zb3VyY2UpO1xuXG4gICAgICBydWxlc1tydWxlTmFtZV0gPSBbXG4gICAgICAgIG9wZXJhdGlvbiwgLy8gXCJkZWZpbmVcIi9cImV4dGVuZFwiL1wib3ZlcnJpZGVcIlxuICAgICAgICBtZXRhSW5mbyxcbiAgICAgICAgZGVzY3JpcHRpb24sXG4gICAgICAgIHJ1bGVJbmZvLmZvcm1hbHMsXG4gICAgICAgIGJvZHlSZWNpcGUsXG4gICAgICBdO1xuICAgIH0pO1xuXG4gICAgLy8gSWYgdGhlIGNhbGxlciBwcm92aWRlZCBhbiBleHByZXNzaW9uIHRvIHVzZSBmb3IgdGhlIHN1cGVyZ3JhbW1hciwgdXNlIHRoYXQuXG4gICAgLy8gT3RoZXJ3aXNlLCBpZiB0aGUgc3VwZXJncmFtbWFyIGlzIGEgdXNlciBncmFtbWFyLCB1c2UgaXRzIHJlY2lwZSBpbmxpbmUuXG4gICAgbGV0IHN1cGVyR3JhbW1hck91dHB1dCA9ICdudWxsJztcbiAgICBpZiAoc3VwZXJHcmFtbWFyRXhwcikge1xuICAgICAgc3VwZXJHcmFtbWFyT3V0cHV0ID0gc3VwZXJHcmFtbWFyRXhwcjtcbiAgICB9IGVsc2UgaWYgKHRoaXMuc3VwZXJHcmFtbWFyICYmICF0aGlzLnN1cGVyR3JhbW1hci5pc0J1aWx0SW4oKSkge1xuICAgICAgc3VwZXJHcmFtbWFyT3V0cHV0ID0gdGhpcy5zdXBlckdyYW1tYXIudG9SZWNpcGUoKTtcbiAgICB9XG5cbiAgICBjb25zdCByZWNpcGVFbGVtZW50cyA9IFtcbiAgICAgIC4uLlsnZ3JhbW1hcicsIG1ldGFJbmZvLCB0aGlzLm5hbWVdLm1hcChKU09OLnN0cmluZ2lmeSksXG4gICAgICBzdXBlckdyYW1tYXJPdXRwdXQsXG4gICAgICAuLi5bc3RhcnRSdWxlLCBydWxlc10ubWFwKEpTT04uc3RyaW5naWZ5KSxcbiAgICBdO1xuICAgIHJldHVybiBqc29uVG9KUyhgWyR7cmVjaXBlRWxlbWVudHMuam9pbignLCcpfV1gKTtcbiAgfVxuXG4gIC8vIFRPRE86IENvbWUgdXAgd2l0aCBiZXR0ZXIgbmFtZXMgZm9yIHRoZXNlIG1ldGhvZHMuXG4gIC8vIFRPRE86IFdyaXRlIHRoZSBhbmFsb2cgb2YgdGhlc2UgbWV0aG9kcyBmb3IgaW5oZXJpdGVkIGF0dHJpYnV0ZXMuXG4gIHRvT3BlcmF0aW9uQWN0aW9uRGljdGlvbmFyeVRlbXBsYXRlKCkge1xuICAgIHJldHVybiB0aGlzLl90b09wZXJhdGlvbk9yQXR0cmlidXRlQWN0aW9uRGljdGlvbmFyeVRlbXBsYXRlKCk7XG4gIH1cbiAgdG9BdHRyaWJ1dGVBY3Rpb25EaWN0aW9uYXJ5VGVtcGxhdGUoKSB7XG4gICAgcmV0dXJuIHRoaXMuX3RvT3BlcmF0aW9uT3JBdHRyaWJ1dGVBY3Rpb25EaWN0aW9uYXJ5VGVtcGxhdGUoKTtcbiAgfVxuXG4gIF90b09wZXJhdGlvbk9yQXR0cmlidXRlQWN0aW9uRGljdGlvbmFyeVRlbXBsYXRlKCkge1xuICAgIC8vIFRPRE86IGFkZCB0aGUgc3VwZXItZ3JhbW1hcidzIHRlbXBsYXRlcyBhdCB0aGUgcmlnaHQgcGxhY2UsIGUuZy4sIGEgY2FzZSBmb3IgQWRkRXhwcl9wbHVzXG4gICAgLy8gc2hvdWxkIGFwcGVhciBuZXh0IHRvIG90aGVyIGNhc2VzIG9mIEFkZEV4cHIuXG5cbiAgICBjb25zdCBzYiA9IG5ldyBjb21tb24uU3RyaW5nQnVmZmVyKCk7XG4gICAgc2IuYXBwZW5kKCd7Jyk7XG5cbiAgICBsZXQgZmlyc3QgPSB0cnVlO1xuXG4gICAgZm9yIChjb25zdCBydWxlTmFtZSBpbiB0aGlzLnJ1bGVzKSB7XG4gICAgICBjb25zdCB7Ym9keX0gPSB0aGlzLnJ1bGVzW3J1bGVOYW1lXTtcbiAgICAgIGlmIChmaXJzdCkge1xuICAgICAgICBmaXJzdCA9IGZhbHNlO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgc2IuYXBwZW5kKCcsJyk7XG4gICAgICB9XG4gICAgICBzYi5hcHBlbmQoJ1xcbicpO1xuICAgICAgc2IuYXBwZW5kKCcgICcpO1xuICAgICAgdGhpcy5hZGRTZW1hbnRpY0FjdGlvblRlbXBsYXRlKHJ1bGVOYW1lLCBib2R5LCBzYik7XG4gICAgfVxuXG4gICAgc2IuYXBwZW5kKCdcXG59Jyk7XG4gICAgcmV0dXJuIHNiLmNvbnRlbnRzKCk7XG4gIH1cblxuICBhZGRTZW1hbnRpY0FjdGlvblRlbXBsYXRlKHJ1bGVOYW1lLCBib2R5LCBzYikge1xuICAgIHNiLmFwcGVuZChydWxlTmFtZSk7XG4gICAgc2IuYXBwZW5kKCc6IGZ1bmN0aW9uKCcpO1xuICAgIGNvbnN0IGFyaXR5ID0gdGhpcy5fdG9wRG93bkFjdGlvbkFyaXR5KHJ1bGVOYW1lKTtcbiAgICBzYi5hcHBlbmQoY29tbW9uLnJlcGVhdCgnXycsIGFyaXR5KS5qb2luKCcsICcpKTtcbiAgICBzYi5hcHBlbmQoJykge1xcbicpO1xuICAgIHNiLmFwcGVuZCgnICB9Jyk7XG4gIH1cblxuICAvLyBQYXJzZSBhIHN0cmluZyB3aGljaCBleHByZXNzZXMgYSBydWxlIGFwcGxpY2F0aW9uIGluIHRoaXMgZ3JhbW1hciwgYW5kIHJldHVybiB0aGVcbiAgLy8gcmVzdWx0aW5nIEFwcGx5IG5vZGUuXG4gIHBhcnNlQXBwbGljYXRpb24oc3RyKSB7XG4gICAgbGV0IGFwcDtcbiAgICBpZiAoc3RyLmluZGV4T2YoJzwnKSA9PT0gLTEpIHtcbiAgICAgIC8vIHNpbXBsZSBhcHBsaWNhdGlvblxuICAgICAgYXBwID0gbmV3IHBleHBycy5BcHBseShzdHIpO1xuICAgIH0gZWxzZSB7XG4gICAgICAvLyBwYXJhbWV0ZXJpemVkIGFwcGxpY2F0aW9uXG4gICAgICBjb25zdCBjc3QgPSBvaG1HcmFtbWFyLm1hdGNoKHN0ciwgJ0Jhc2VfYXBwbGljYXRpb24nKTtcbiAgICAgIGFwcCA9IGJ1aWxkR3JhbW1hcihjc3QsIHt9KTtcbiAgICB9XG5cbiAgICAvLyBFbnN1cmUgdGhhdCB0aGUgYXBwbGljYXRpb24gaXMgdmFsaWQuXG4gICAgaWYgKCEoYXBwLnJ1bGVOYW1lIGluIHRoaXMucnVsZXMpKSB7XG4gICAgICB0aHJvdyBlcnJvcnMudW5kZWNsYXJlZFJ1bGUoYXBwLnJ1bGVOYW1lLCB0aGlzLm5hbWUpO1xuICAgIH1cbiAgICBjb25zdCB7Zm9ybWFsc30gPSB0aGlzLnJ1bGVzW2FwcC5ydWxlTmFtZV07XG4gICAgaWYgKGZvcm1hbHMubGVuZ3RoICE9PSBhcHAuYXJncy5sZW5ndGgpIHtcbiAgICAgIGNvbnN0IHtzb3VyY2V9ID0gdGhpcy5ydWxlc1thcHAucnVsZU5hbWVdO1xuICAgICAgdGhyb3cgZXJyb3JzLndyb25nTnVtYmVyT2ZQYXJhbWV0ZXJzKFxuICAgICAgICBhcHAucnVsZU5hbWUsXG4gICAgICAgIGZvcm1hbHMubGVuZ3RoLFxuICAgICAgICBhcHAuYXJncy5sZW5ndGgsXG4gICAgICAgIHNvdXJjZVxuICAgICAgKTtcbiAgICB9XG4gICAgcmV0dXJuIGFwcDtcbiAgfVxuXG4gIF9zZXRVcE1hdGNoU3RhdGUoc3RhdGUpIHtcbiAgICBpZiAodGhpcy5fbWF0Y2hTdGF0ZUluaXRpYWxpemVyKSB7XG4gICAgICB0aGlzLl9tYXRjaFN0YXRlSW5pdGlhbGl6ZXIoc3RhdGUpO1xuICAgIH1cbiAgfVxufVxuXG4vLyBUaGUgZm9sbG93aW5nIGdyYW1tYXIgY29udGFpbnMgYSBmZXcgcnVsZXMgdGhhdCBjb3VsZG4ndCBiZSB3cml0dGVuICBpbiBcInVzZXJsYW5kXCIuXG4vLyBBdCB0aGUgYm90dG9tIG9mIHNyYy9tYWluLmpzLCB3ZSBjcmVhdGUgYSBzdWItZ3JhbW1hciBvZiB0aGlzIGdyYW1tYXIgdGhhdCdzIGNhbGxlZFxuLy8gYEJ1aWx0SW5SdWxlc2AuIFRoYXQgZ3JhbW1hciBjb250YWlucyBzZXZlcmFsIGNvbnZlbmllbmNlIHJ1bGVzLCBlLmcuLCBgbGV0dGVyYCBhbmRcbi8vIGBkaWdpdGAsIGFuZCBpcyBpbXBsaWNpdGx5IHRoZSBzdXBlci1ncmFtbWFyIG9mIGFueSBncmFtbWFyIHdob3NlIHN1cGVyLWdyYW1tYXJcbi8vIGlzbid0IHNwZWNpZmllZC5cbkdyYW1tYXIuUHJvdG9CdWlsdEluUnVsZXMgPSBuZXcgR3JhbW1hcihcbiAgJ1Byb3RvQnVpbHRJblJ1bGVzJywgLy8gbmFtZVxuICB1bmRlZmluZWQsIC8vIHN1cGVyZ3JhbW1hclxuICB7XG4gICAgYW55OiB7XG4gICAgICBib2R5OiBwZXhwcnMuYW55LFxuICAgICAgZm9ybWFsczogW10sXG4gICAgICBkZXNjcmlwdGlvbjogJ2FueSBjaGFyYWN0ZXInLFxuICAgICAgcHJpbWl0aXZlOiB0cnVlLFxuICAgIH0sXG4gICAgZW5kOiB7XG4gICAgICBib2R5OiBwZXhwcnMuZW5kLFxuICAgICAgZm9ybWFsczogW10sXG4gICAgICBkZXNjcmlwdGlvbjogJ2VuZCBvZiBpbnB1dCcsXG4gICAgICBwcmltaXRpdmU6IHRydWUsXG4gICAgfSxcblxuICAgIGNhc2VJbnNlbnNpdGl2ZToge1xuICAgICAgYm9keTogbmV3IHBleHBycy5DYXNlSW5zZW5zaXRpdmVUZXJtaW5hbChuZXcgcGV4cHJzLlBhcmFtKDApKSxcbiAgICAgIGZvcm1hbHM6IFsnc3RyJ10sXG4gICAgICBwcmltaXRpdmU6IHRydWUsXG4gICAgfSxcbiAgICBsb3dlcjoge1xuICAgICAgYm9keTogbmV3IHBleHBycy5Vbmljb2RlQ2hhcignTGwnKSxcbiAgICAgIGZvcm1hbHM6IFtdLFxuICAgICAgZGVzY3JpcHRpb246ICdhIGxvd2VyY2FzZSBsZXR0ZXInLFxuICAgICAgcHJpbWl0aXZlOiB0cnVlLFxuICAgIH0sXG4gICAgdXBwZXI6IHtcbiAgICAgIGJvZHk6IG5ldyBwZXhwcnMuVW5pY29kZUNoYXIoJ0x1JyksXG4gICAgICBmb3JtYWxzOiBbXSxcbiAgICAgIGRlc2NyaXB0aW9uOiAnYW4gdXBwZXJjYXNlIGxldHRlcicsXG4gICAgICBwcmltaXRpdmU6IHRydWUsXG4gICAgfSxcbiAgICAvLyBVbmlvbiBvZiBMdCAodGl0bGVjYXNlKSwgTG0gKG1vZGlmaWVyKSwgYW5kIExvIChvdGhlciksIGkuZS4gYW55IGxldHRlciBub3QgaW4gTGwgb3IgTHUuXG4gICAgdW5pY29kZUx0bW86IHtcbiAgICAgIGJvZHk6IG5ldyBwZXhwcnMuVW5pY29kZUNoYXIoJ0x0bW8nKSxcbiAgICAgIGZvcm1hbHM6IFtdLFxuICAgICAgZGVzY3JpcHRpb246ICdhIFVuaWNvZGUgY2hhcmFjdGVyIGluIEx0LCBMbSwgb3IgTG8nLFxuICAgICAgcHJpbWl0aXZlOiB0cnVlLFxuICAgIH0sXG5cbiAgICAvLyBUaGVzZSBydWxlcyBhcmUgbm90IHRydWx5IHByaW1pdGl2ZSAodGhleSBjb3VsZCBiZSB3cml0dGVuIGluIHVzZXJsYW5kKSBidXQgYXJlIGRlZmluZWRcbiAgICAvLyBoZXJlIGZvciBib290c3RyYXBwaW5nIHB1cnBvc2VzLlxuICAgIHNwYWNlczoge1xuICAgICAgYm9keTogbmV3IHBleHBycy5TdGFyKG5ldyBwZXhwcnMuQXBwbHkoJ3NwYWNlJykpLFxuICAgICAgZm9ybWFsczogW10sXG4gICAgfSxcbiAgICBzcGFjZToge1xuICAgICAgYm9keTogbmV3IHBleHBycy5SYW5nZSgnXFx4MDAnLCAnICcpLFxuICAgICAgZm9ybWFsczogW10sXG4gICAgICBkZXNjcmlwdGlvbjogJ2Egc3BhY2UnLFxuICAgIH0sXG4gIH1cbik7XG5cbi8vIFRoaXMgbWV0aG9kIGlzIGNhbGxlZCBmcm9tIG1haW4uanMgb25jZSBPaG0gaGFzIGxvYWRlZC5cbkdyYW1tYXIuaW5pdEFwcGxpY2F0aW9uUGFyc2VyID0gZnVuY3Rpb24gKGdyYW1tYXIsIGJ1aWxkZXJGbikge1xuICBvaG1HcmFtbWFyID0gZ3JhbW1hcjtcbiAgYnVpbGRHcmFtbWFyID0gYnVpbGRlckZuO1xufTtcbiIsImltcG9ydCB7R3JhbW1hcn0gZnJvbSAnLi9HcmFtbWFyLmpzJztcbmltcG9ydCB7SW5wdXRTdHJlYW19IGZyb20gJy4vSW5wdXRTdHJlYW0uanMnO1xuaW1wb3J0IHtnZXREdXBsaWNhdGVzfSBmcm9tICcuL2NvbW1vbi5qcyc7XG5pbXBvcnQgKiBhcyBlcnJvcnMgZnJvbSAnLi9lcnJvcnMuanMnO1xuaW1wb3J0ICogYXMgcGV4cHJzIGZyb20gJy4vcGV4cHJzLmpzJztcblxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS1cbi8vIFByaXZhdGUgU3R1ZmZcbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG5cbi8vIENvbnN0cnVjdG9yc1xuXG5leHBvcnQgY2xhc3MgR3JhbW1hckRlY2wge1xuICBjb25zdHJ1Y3RvcihuYW1lKSB7XG4gICAgdGhpcy5uYW1lID0gbmFtZTtcbiAgfVxuXG4gIC8vIEhlbHBlcnNcblxuICBzb3VyY2VJbnRlcnZhbChzdGFydElkeCwgZW5kSWR4KSB7XG4gICAgcmV0dXJuIHRoaXMuc291cmNlLnN1YkludGVydmFsKHN0YXJ0SWR4LCBlbmRJZHggLSBzdGFydElkeCk7XG4gIH1cblxuICBlbnN1cmVTdXBlckdyYW1tYXIoKSB7XG4gICAgaWYgKCF0aGlzLnN1cGVyR3JhbW1hcikge1xuICAgICAgdGhpcy53aXRoU3VwZXJHcmFtbWFyKFxuICAgICAgICAvLyBUT0RPOiBUaGUgY29uZGl0aW9uYWwgZXhwcmVzc2lvbiBiZWxvdyBpcyBhbiB1Z2x5IGhhY2suIEl0J3Mga2luZCBvZiBvayBiZWNhdXNlXG4gICAgICAgIC8vIEkgZG91YnQgYW55b25lIHdpbGwgZXZlciB0cnkgdG8gZGVjbGFyZSBhIGdyYW1tYXIgY2FsbGVkIGBCdWlsdEluUnVsZXNgLiBTdGlsbCxcbiAgICAgICAgLy8gd2Ugc2hvdWxkIHRyeSB0byBmaW5kIGEgYmV0dGVyIHdheSB0byBkbyB0aGlzLlxuICAgICAgICB0aGlzLm5hbWUgPT09ICdCdWlsdEluUnVsZXMnID8gR3JhbW1hci5Qcm90b0J1aWx0SW5SdWxlcyA6IEdyYW1tYXIuQnVpbHRJblJ1bGVzXG4gICAgICApO1xuICAgIH1cbiAgICByZXR1cm4gdGhpcy5zdXBlckdyYW1tYXI7XG4gIH1cblxuICBlbnN1cmVTdXBlckdyYW1tYXJSdWxlRm9yT3ZlcnJpZGluZyhuYW1lLCBzb3VyY2UpIHtcbiAgICBjb25zdCBydWxlSW5mbyA9IHRoaXMuZW5zdXJlU3VwZXJHcmFtbWFyKCkucnVsZXNbbmFtZV07XG4gICAgaWYgKCFydWxlSW5mbykge1xuICAgICAgdGhyb3cgZXJyb3JzLmNhbm5vdE92ZXJyaWRlVW5kZWNsYXJlZFJ1bGUobmFtZSwgdGhpcy5zdXBlckdyYW1tYXIubmFtZSwgc291cmNlKTtcbiAgICB9XG4gICAgcmV0dXJuIHJ1bGVJbmZvO1xuICB9XG5cbiAgaW5zdGFsbE92ZXJyaWRkZW5PckV4dGVuZGVkUnVsZShuYW1lLCBmb3JtYWxzLCBib2R5LCBzb3VyY2UpIHtcbiAgICBjb25zdCBkdXBsaWNhdGVQYXJhbWV0ZXJOYW1lcyA9IGdldER1cGxpY2F0ZXMoZm9ybWFscyk7XG4gICAgaWYgKGR1cGxpY2F0ZVBhcmFtZXRlck5hbWVzLmxlbmd0aCA+IDApIHtcbiAgICAgIHRocm93IGVycm9ycy5kdXBsaWNhdGVQYXJhbWV0ZXJOYW1lcyhuYW1lLCBkdXBsaWNhdGVQYXJhbWV0ZXJOYW1lcywgc291cmNlKTtcbiAgICB9XG4gICAgY29uc3QgcnVsZUluZm8gPSB0aGlzLmVuc3VyZVN1cGVyR3JhbW1hcigpLnJ1bGVzW25hbWVdO1xuICAgIGNvbnN0IGV4cGVjdGVkRm9ybWFscyA9IHJ1bGVJbmZvLmZvcm1hbHM7XG4gICAgY29uc3QgZXhwZWN0ZWROdW1Gb3JtYWxzID0gZXhwZWN0ZWRGb3JtYWxzID8gZXhwZWN0ZWRGb3JtYWxzLmxlbmd0aCA6IDA7XG4gICAgaWYgKGZvcm1hbHMubGVuZ3RoICE9PSBleHBlY3RlZE51bUZvcm1hbHMpIHtcbiAgICAgIHRocm93IGVycm9ycy53cm9uZ051bWJlck9mUGFyYW1ldGVycyhuYW1lLCBleHBlY3RlZE51bUZvcm1hbHMsIGZvcm1hbHMubGVuZ3RoLCBzb3VyY2UpO1xuICAgIH1cbiAgICByZXR1cm4gdGhpcy5pbnN0YWxsKG5hbWUsIGZvcm1hbHMsIGJvZHksIHJ1bGVJbmZvLmRlc2NyaXB0aW9uLCBzb3VyY2UpO1xuICB9XG5cbiAgaW5zdGFsbChuYW1lLCBmb3JtYWxzLCBib2R5LCBkZXNjcmlwdGlvbiwgc291cmNlLCBwcmltaXRpdmUgPSBmYWxzZSkge1xuICAgIHRoaXMucnVsZXNbbmFtZV0gPSB7XG4gICAgICBib2R5OiBib2R5LmludHJvZHVjZVBhcmFtcyhmb3JtYWxzKSxcbiAgICAgIGZvcm1hbHMsXG4gICAgICBkZXNjcmlwdGlvbixcbiAgICAgIHNvdXJjZSxcbiAgICAgIHByaW1pdGl2ZSxcbiAgICB9O1xuICAgIHJldHVybiB0aGlzO1xuICB9XG5cbiAgLy8gU3R1ZmYgdGhhdCB5b3Ugc2hvdWxkIG9ubHkgZG8gb25jZVxuXG4gIHdpdGhTdXBlckdyYW1tYXIoc3VwZXJHcmFtbWFyKSB7XG4gICAgaWYgKHRoaXMuc3VwZXJHcmFtbWFyKSB7XG4gICAgICB0aHJvdyBuZXcgRXJyb3IoJ3RoZSBzdXBlciBncmFtbWFyIG9mIGEgR3JhbW1hckRlY2wgY2Fubm90IGJlIHNldCBtb3JlIHRoYW4gb25jZScpO1xuICAgIH1cbiAgICB0aGlzLnN1cGVyR3JhbW1hciA9IHN1cGVyR3JhbW1hcjtcbiAgICB0aGlzLnJ1bGVzID0gT2JqZWN0LmNyZWF0ZShzdXBlckdyYW1tYXIucnVsZXMpO1xuXG4gICAgLy8gR3JhbW1hcnMgd2l0aCBhbiBleHBsaWNpdCBzdXBlcmdyYW1tYXIgaW5oZXJpdCBhIGRlZmF1bHQgc3RhcnQgcnVsZS5cbiAgICBpZiAoIXN1cGVyR3JhbW1hci5pc0J1aWx0SW4oKSkge1xuICAgICAgdGhpcy5kZWZhdWx0U3RhcnRSdWxlID0gc3VwZXJHcmFtbWFyLmRlZmF1bHRTdGFydFJ1bGU7XG4gICAgfVxuICAgIHJldHVybiB0aGlzO1xuICB9XG5cbiAgd2l0aERlZmF1bHRTdGFydFJ1bGUocnVsZU5hbWUpIHtcbiAgICB0aGlzLmRlZmF1bHRTdGFydFJ1bGUgPSBydWxlTmFtZTtcbiAgICByZXR1cm4gdGhpcztcbiAgfVxuXG4gIHdpdGhTb3VyY2Uoc291cmNlKSB7XG4gICAgdGhpcy5zb3VyY2UgPSBuZXcgSW5wdXRTdHJlYW0oc291cmNlKS5pbnRlcnZhbCgwLCBzb3VyY2UubGVuZ3RoKTtcbiAgICByZXR1cm4gdGhpcztcbiAgfVxuXG4gIC8vIENyZWF0ZXMgYSBHcmFtbWFyIGluc3RhbmNlLCBhbmQgaWYgaXQgcGFzc2VzIHRoZSBzYW5pdHkgY2hlY2tzLCByZXR1cm5zIGl0LlxuICBidWlsZCgpIHtcbiAgICBjb25zdCBncmFtbWFyID0gbmV3IEdyYW1tYXIoXG4gICAgICB0aGlzLm5hbWUsXG4gICAgICB0aGlzLmVuc3VyZVN1cGVyR3JhbW1hcigpLFxuICAgICAgdGhpcy5ydWxlcyxcbiAgICAgIHRoaXMuZGVmYXVsdFN0YXJ0UnVsZVxuICAgICk7XG4gICAgLy8gSW5pdGlhbGl6ZSBpbnRlcm5hbCBwcm9wcyB0aGF0IGFyZSBpbmhlcml0ZWQgZnJvbSB0aGUgc3VwZXIgZ3JhbW1hci5cbiAgICBncmFtbWFyLl9tYXRjaFN0YXRlSW5pdGlhbGl6ZXIgPSBncmFtbWFyLnN1cGVyR3JhbW1hci5fbWF0Y2hTdGF0ZUluaXRpYWxpemVyO1xuICAgIGdyYW1tYXIuc3VwcG9ydHNJbmNyZW1lbnRhbFBhcnNpbmcgPSBncmFtbWFyLnN1cGVyR3JhbW1hci5zdXBwb3J0c0luY3JlbWVudGFsUGFyc2luZztcblxuICAgIC8vIFRPRE86IGNoYW5nZSB0aGUgcGV4cHIucHJvdG90eXBlLmFzc2VydC4uLiBtZXRob2RzIHRvIG1ha2UgdGhlbSBhZGRcbiAgICAvLyBleGNlcHRpb25zIHRvIGFuIGFycmF5IHRoYXQncyBwcm92aWRlZCBhcyBhbiBhcmcuIFRoZW4gd2UnbGwgYmUgYWJsZSB0b1xuICAgIC8vIHNob3cgbW9yZSB0aGFuIG9uZSBlcnJvciBvZiB0aGUgc2FtZSB0eXBlIGF0IGEgdGltZS5cbiAgICAvLyBUT0RPOiBpbmNsdWRlIHRoZSBvZmZlbmRpbmcgcGV4cHIgaW4gdGhlIGVycm9ycywgdGhhdCB3YXkgd2UgY2FuIHNob3dcbiAgICAvLyB0aGUgcGFydCBvZiB0aGUgc291cmNlIHRoYXQgY2F1c2VkIGl0LlxuICAgIGNvbnN0IGdyYW1tYXJFcnJvcnMgPSBbXTtcbiAgICBsZXQgZ3JhbW1hckhhc0ludmFsaWRBcHBsaWNhdGlvbnMgPSBmYWxzZTtcbiAgICBPYmplY3Qua2V5cyhncmFtbWFyLnJ1bGVzKS5mb3JFYWNoKHJ1bGVOYW1lID0+IHtcbiAgICAgIGNvbnN0IHtib2R5fSA9IGdyYW1tYXIucnVsZXNbcnVsZU5hbWVdO1xuICAgICAgdHJ5IHtcbiAgICAgICAgYm9keS5hc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eShydWxlTmFtZSk7XG4gICAgICB9IGNhdGNoIChlKSB7XG4gICAgICAgIGdyYW1tYXJFcnJvcnMucHVzaChlKTtcbiAgICAgIH1cbiAgICAgIHRyeSB7XG4gICAgICAgIGJvZHkuYXNzZXJ0QWxsQXBwbGljYXRpb25zQXJlVmFsaWQocnVsZU5hbWUsIGdyYW1tYXIpO1xuICAgICAgfSBjYXRjaCAoZSkge1xuICAgICAgICBncmFtbWFyRXJyb3JzLnB1c2goZSk7XG4gICAgICAgIGdyYW1tYXJIYXNJbnZhbGlkQXBwbGljYXRpb25zID0gdHJ1ZTtcbiAgICAgIH1cbiAgICB9KTtcbiAgICBpZiAoIWdyYW1tYXJIYXNJbnZhbGlkQXBwbGljYXRpb25zKSB7XG4gICAgICAvLyBUaGUgZm9sbG93aW5nIGNoZWNrIGNhbiBvbmx5IGJlIGRvbmUgaWYgdGhlIGdyYW1tYXIgaGFzIG5vIGludmFsaWQgYXBwbGljYXRpb25zLlxuICAgICAgT2JqZWN0LmtleXMoZ3JhbW1hci5ydWxlcykuZm9yRWFjaChydWxlTmFtZSA9PiB7XG4gICAgICAgIGNvbnN0IHtib2R5fSA9IGdyYW1tYXIucnVsZXNbcnVsZU5hbWVdO1xuICAgICAgICB0cnkge1xuICAgICAgICAgIGJvZHkuYXNzZXJ0SXRlcmF0ZWRFeHByc0FyZU5vdE51bGxhYmxlKGdyYW1tYXIsIFtdKTtcbiAgICAgICAgfSBjYXRjaCAoZSkge1xuICAgICAgICAgIGdyYW1tYXJFcnJvcnMucHVzaChlKTtcbiAgICAgICAgfVxuICAgICAgfSk7XG4gICAgfVxuICAgIGlmIChncmFtbWFyRXJyb3JzLmxlbmd0aCA+IDApIHtcbiAgICAgIGVycm9ycy50aHJvd0Vycm9ycyhncmFtbWFyRXJyb3JzKTtcbiAgICB9XG4gICAgaWYgKHRoaXMuc291cmNlKSB7XG4gICAgICBncmFtbWFyLnNvdXJjZSA9IHRoaXMuc291cmNlO1xuICAgIH1cblxuICAgIHJldHVybiBncmFtbWFyO1xuICB9XG5cbiAgLy8gUnVsZSBkZWNsYXJhdGlvbnNcblxuICBkZWZpbmUobmFtZSwgZm9ybWFscywgYm9keSwgZGVzY3JpcHRpb24sIHNvdXJjZSwgcHJpbWl0aXZlKSB7XG4gICAgdGhpcy5lbnN1cmVTdXBlckdyYW1tYXIoKTtcbiAgICBpZiAodGhpcy5zdXBlckdyYW1tYXIucnVsZXNbbmFtZV0pIHtcbiAgICAgIHRocm93IGVycm9ycy5kdXBsaWNhdGVSdWxlRGVjbGFyYXRpb24obmFtZSwgdGhpcy5uYW1lLCB0aGlzLnN1cGVyR3JhbW1hci5uYW1lLCBzb3VyY2UpO1xuICAgIH0gZWxzZSBpZiAodGhpcy5ydWxlc1tuYW1lXSkge1xuICAgICAgdGhyb3cgZXJyb3JzLmR1cGxpY2F0ZVJ1bGVEZWNsYXJhdGlvbihuYW1lLCB0aGlzLm5hbWUsIHRoaXMubmFtZSwgc291cmNlKTtcbiAgICB9XG4gICAgY29uc3QgZHVwbGljYXRlUGFyYW1ldGVyTmFtZXMgPSBnZXREdXBsaWNhdGVzKGZvcm1hbHMpO1xuICAgIGlmIChkdXBsaWNhdGVQYXJhbWV0ZXJOYW1lcy5sZW5ndGggPiAwKSB7XG4gICAgICB0aHJvdyBlcnJvcnMuZHVwbGljYXRlUGFyYW1ldGVyTmFtZXMobmFtZSwgZHVwbGljYXRlUGFyYW1ldGVyTmFtZXMsIHNvdXJjZSk7XG4gICAgfVxuICAgIHJldHVybiB0aGlzLmluc3RhbGwobmFtZSwgZm9ybWFscywgYm9keSwgZGVzY3JpcHRpb24sIHNvdXJjZSwgcHJpbWl0aXZlKTtcbiAgfVxuXG4gIG92ZXJyaWRlKG5hbWUsIGZvcm1hbHMsIGJvZHksIGRlc2NJZ25vcmVkLCBzb3VyY2UpIHtcbiAgICB0aGlzLmVuc3VyZVN1cGVyR3JhbW1hclJ1bGVGb3JPdmVycmlkaW5nKG5hbWUsIHNvdXJjZSk7XG4gICAgdGhpcy5pbnN0YWxsT3ZlcnJpZGRlbk9yRXh0ZW5kZWRSdWxlKG5hbWUsIGZvcm1hbHMsIGJvZHksIHNvdXJjZSk7XG4gICAgcmV0dXJuIHRoaXM7XG4gIH1cblxuICBleHRlbmQobmFtZSwgZm9ybWFscywgZnJhZ21lbnQsIGRlc2NJZ25vcmVkLCBzb3VyY2UpIHtcbiAgICBjb25zdCBydWxlSW5mbyA9IHRoaXMuZW5zdXJlU3VwZXJHcmFtbWFyKCkucnVsZXNbbmFtZV07XG4gICAgaWYgKCFydWxlSW5mbykge1xuICAgICAgdGhyb3cgZXJyb3JzLmNhbm5vdEV4dGVuZFVuZGVjbGFyZWRSdWxlKG5hbWUsIHRoaXMuc3VwZXJHcmFtbWFyLm5hbWUsIHNvdXJjZSk7XG4gICAgfVxuICAgIGNvbnN0IGJvZHkgPSBuZXcgcGV4cHJzLkV4dGVuZCh0aGlzLnN1cGVyR3JhbW1hciwgbmFtZSwgZnJhZ21lbnQpO1xuICAgIGJvZHkuc291cmNlID0gZnJhZ21lbnQuc291cmNlO1xuICAgIHRoaXMuaW5zdGFsbE92ZXJyaWRkZW5PckV4dGVuZGVkUnVsZShuYW1lLCBmb3JtYWxzLCBib2R5LCBzb3VyY2UpO1xuICAgIHJldHVybiB0aGlzO1xuICB9XG59XG4iLCJpbXBvcnQge0dyYW1tYXJ9IGZyb20gJy4vR3JhbW1hci5qcyc7XG5pbXBvcnQge0dyYW1tYXJEZWNsfSBmcm9tICcuL0dyYW1tYXJEZWNsLmpzJztcbmltcG9ydCAqIGFzIHBleHBycyBmcm9tICcuL3BleHBycy5qcyc7XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG4vLyBQcml2YXRlIHN0dWZmXG4vLyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuXG5leHBvcnQgY2xhc3MgQnVpbGRlciB7XG4gIGNvbnN0cnVjdG9yKG9wdGlvbnMpIHtcbiAgICB0aGlzLmN1cnJlbnREZWNsID0gbnVsbDtcbiAgICB0aGlzLmN1cnJlbnRSdWxlTmFtZSA9IG51bGw7XG4gICAgdGhpcy5vcHRpb25zID0gb3B0aW9ucyB8fCB7fTtcbiAgfVxuXG4gIG5ld0dyYW1tYXIobmFtZSkge1xuICAgIHJldHVybiBuZXcgR3JhbW1hckRlY2wobmFtZSk7XG4gIH1cblxuICBncmFtbWFyKG1ldGFJbmZvLCBuYW1lLCBzdXBlckdyYW1tYXIsIGRlZmF1bHRTdGFydFJ1bGUsIHJ1bGVzKSB7XG4gICAgY29uc3QgZ0RlY2wgPSBuZXcgR3JhbW1hckRlY2wobmFtZSk7XG4gICAgaWYgKHN1cGVyR3JhbW1hcikge1xuICAgICAgLy8gYHN1cGVyR3JhbW1hcmAgbWF5IGJlIGEgcmVjaXBlIChpLmUuIGFuIEFycmF5KSwgb3IgYW4gYWN0dWFsIGdyYW1tYXIgaW5zdGFuY2UuXG4gICAgICBnRGVjbC53aXRoU3VwZXJHcmFtbWFyKFxuICAgICAgICBzdXBlckdyYW1tYXIgaW5zdGFuY2VvZiBHcmFtbWFyID8gc3VwZXJHcmFtbWFyIDogdGhpcy5mcm9tUmVjaXBlKHN1cGVyR3JhbW1hcilcbiAgICAgICk7XG4gICAgfVxuICAgIGlmIChkZWZhdWx0U3RhcnRSdWxlKSB7XG4gICAgICBnRGVjbC53aXRoRGVmYXVsdFN0YXJ0UnVsZShkZWZhdWx0U3RhcnRSdWxlKTtcbiAgICB9XG4gICAgaWYgKG1ldGFJbmZvICYmIG1ldGFJbmZvLnNvdXJjZSkge1xuICAgICAgZ0RlY2wud2l0aFNvdXJjZShtZXRhSW5mby5zb3VyY2UpO1xuICAgIH1cblxuICAgIHRoaXMuY3VycmVudERlY2wgPSBnRGVjbDtcbiAgICBPYmplY3Qua2V5cyhydWxlcykuZm9yRWFjaChydWxlTmFtZSA9PiB7XG4gICAgICB0aGlzLmN1cnJlbnRSdWxlTmFtZSA9IHJ1bGVOYW1lO1xuICAgICAgY29uc3QgcnVsZVJlY2lwZSA9IHJ1bGVzW3J1bGVOYW1lXTtcblxuICAgICAgY29uc3QgYWN0aW9uID0gcnVsZVJlY2lwZVswXTsgLy8gZGVmaW5lL2V4dGVuZC9vdmVycmlkZVxuICAgICAgY29uc3QgbWV0YUluZm8gPSBydWxlUmVjaXBlWzFdO1xuICAgICAgY29uc3QgZGVzY3JpcHRpb24gPSBydWxlUmVjaXBlWzJdO1xuICAgICAgY29uc3QgZm9ybWFscyA9IHJ1bGVSZWNpcGVbM107XG4gICAgICBjb25zdCBib2R5ID0gdGhpcy5mcm9tUmVjaXBlKHJ1bGVSZWNpcGVbNF0pO1xuXG4gICAgICBsZXQgc291cmNlO1xuICAgICAgaWYgKGdEZWNsLnNvdXJjZSAmJiBtZXRhSW5mbyAmJiBtZXRhSW5mby5zb3VyY2VJbnRlcnZhbCkge1xuICAgICAgICBzb3VyY2UgPSBnRGVjbC5zb3VyY2Uuc3ViSW50ZXJ2YWwoXG4gICAgICAgICAgbWV0YUluZm8uc291cmNlSW50ZXJ2YWxbMF0sXG4gICAgICAgICAgbWV0YUluZm8uc291cmNlSW50ZXJ2YWxbMV0gLSBtZXRhSW5mby5zb3VyY2VJbnRlcnZhbFswXVxuICAgICAgICApO1xuICAgICAgfVxuICAgICAgZ0RlY2xbYWN0aW9uXShydWxlTmFtZSwgZm9ybWFscywgYm9keSwgZGVzY3JpcHRpb24sIHNvdXJjZSk7XG4gICAgfSk7XG4gICAgdGhpcy5jdXJyZW50UnVsZU5hbWUgPSB0aGlzLmN1cnJlbnREZWNsID0gbnVsbDtcbiAgICByZXR1cm4gZ0RlY2wuYnVpbGQoKTtcbiAgfVxuXG4gIHRlcm1pbmFsKHgpIHtcbiAgICByZXR1cm4gbmV3IHBleHBycy5UZXJtaW5hbCh4KTtcbiAgfVxuXG4gIHJhbmdlKGZyb20sIHRvKSB7XG4gICAgcmV0dXJuIG5ldyBwZXhwcnMuUmFuZ2UoZnJvbSwgdG8pO1xuICB9XG5cbiAgcGFyYW0oaW5kZXgpIHtcbiAgICByZXR1cm4gbmV3IHBleHBycy5QYXJhbShpbmRleCk7XG4gIH1cblxuICBhbHQoLi4udGVybUFyZ3MpIHtcbiAgICBsZXQgdGVybXMgPSBbXTtcbiAgICBmb3IgKGxldCBhcmcgb2YgdGVybUFyZ3MpIHtcbiAgICAgIGlmICghKGFyZyBpbnN0YW5jZW9mIHBleHBycy5QRXhwcikpIHtcbiAgICAgICAgYXJnID0gdGhpcy5mcm9tUmVjaXBlKGFyZyk7XG4gICAgICB9XG4gICAgICBpZiAoYXJnIGluc3RhbmNlb2YgcGV4cHJzLkFsdCkge1xuICAgICAgICB0ZXJtcyA9IHRlcm1zLmNvbmNhdChhcmcudGVybXMpO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgdGVybXMucHVzaChhcmcpO1xuICAgICAgfVxuICAgIH1cbiAgICByZXR1cm4gdGVybXMubGVuZ3RoID09PSAxID8gdGVybXNbMF0gOiBuZXcgcGV4cHJzLkFsdCh0ZXJtcyk7XG4gIH1cblxuICBzZXEoLi4uZmFjdG9yQXJncykge1xuICAgIGxldCBmYWN0b3JzID0gW107XG4gICAgZm9yIChsZXQgYXJnIG9mIGZhY3RvckFyZ3MpIHtcbiAgICAgIGlmICghKGFyZyBpbnN0YW5jZW9mIHBleHBycy5QRXhwcikpIHtcbiAgICAgICAgYXJnID0gdGhpcy5mcm9tUmVjaXBlKGFyZyk7XG4gICAgICB9XG4gICAgICBpZiAoYXJnIGluc3RhbmNlb2YgcGV4cHJzLlNlcSkge1xuICAgICAgICBmYWN0b3JzID0gZmFjdG9ycy5jb25jYXQoYXJnLmZhY3RvcnMpO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgZmFjdG9ycy5wdXNoKGFyZyk7XG4gICAgICB9XG4gICAgfVxuICAgIHJldHVybiBmYWN0b3JzLmxlbmd0aCA9PT0gMSA/IGZhY3RvcnNbMF0gOiBuZXcgcGV4cHJzLlNlcShmYWN0b3JzKTtcbiAgfVxuXG4gIHN0YXIoZXhwcikge1xuICAgIGlmICghKGV4cHIgaW5zdGFuY2VvZiBwZXhwcnMuUEV4cHIpKSB7XG4gICAgICBleHByID0gdGhpcy5mcm9tUmVjaXBlKGV4cHIpO1xuICAgIH1cbiAgICByZXR1cm4gbmV3IHBleHBycy5TdGFyKGV4cHIpO1xuICB9XG5cbiAgcGx1cyhleHByKSB7XG4gICAgaWYgKCEoZXhwciBpbnN0YW5jZW9mIHBleHBycy5QRXhwcikpIHtcbiAgICAgIGV4cHIgPSB0aGlzLmZyb21SZWNpcGUoZXhwcik7XG4gICAgfVxuICAgIHJldHVybiBuZXcgcGV4cHJzLlBsdXMoZXhwcik7XG4gIH1cblxuICBvcHQoZXhwcikge1xuICAgIGlmICghKGV4cHIgaW5zdGFuY2VvZiBwZXhwcnMuUEV4cHIpKSB7XG4gICAgICBleHByID0gdGhpcy5mcm9tUmVjaXBlKGV4cHIpO1xuICAgIH1cbiAgICByZXR1cm4gbmV3IHBleHBycy5PcHQoZXhwcik7XG4gIH1cblxuICBub3QoZXhwcikge1xuICAgIGlmICghKGV4cHIgaW5zdGFuY2VvZiBwZXhwcnMuUEV4cHIpKSB7XG4gICAgICBleHByID0gdGhpcy5mcm9tUmVjaXBlKGV4cHIpO1xuICAgIH1cbiAgICByZXR1cm4gbmV3IHBleHBycy5Ob3QoZXhwcik7XG4gIH1cblxuICBsb29rYWhlYWQoZXhwcikge1xuICAgIGlmICghKGV4cHIgaW5zdGFuY2VvZiBwZXhwcnMuUEV4cHIpKSB7XG4gICAgICBleHByID0gdGhpcy5mcm9tUmVjaXBlKGV4cHIpO1xuICAgIH1cbiAgICAvLyBGb3IgdjE4IGNvbXBhdGliaWxpdHksIHdoZXJlIHdlIGRvbid0IHdhbnQgYSBiaW5kaW5nIGZvciBsb29rYWhlYWQuXG4gICAgaWYgKHRoaXMub3B0aW9ucy5lbGltaW5hdGVMb29rYWhlYWRzKSB7XG4gICAgICByZXR1cm4gbmV3IHBleHBycy5Ob3QobmV3IHBleHBycy5Ob3QoZXhwcikpO1xuICAgIH1cbiAgICByZXR1cm4gbmV3IHBleHBycy5Mb29rYWhlYWQoZXhwcik7XG4gIH1cblxuICBsZXgoZXhwcikge1xuICAgIGlmICghKGV4cHIgaW5zdGFuY2VvZiBwZXhwcnMuUEV4cHIpKSB7XG4gICAgICBleHByID0gdGhpcy5mcm9tUmVjaXBlKGV4cHIpO1xuICAgIH1cbiAgICByZXR1cm4gbmV3IHBleHBycy5MZXgoZXhwcik7XG4gIH1cblxuICBhcHAocnVsZU5hbWUsIG9wdFBhcmFtcykge1xuICAgIGlmIChvcHRQYXJhbXMgJiYgb3B0UGFyYW1zLmxlbmd0aCA+IDApIHtcbiAgICAgIG9wdFBhcmFtcyA9IG9wdFBhcmFtcy5tYXAoZnVuY3Rpb24gKHBhcmFtKSB7XG4gICAgICAgIHJldHVybiBwYXJhbSBpbnN0YW5jZW9mIHBleHBycy5QRXhwciA/IHBhcmFtIDogdGhpcy5mcm9tUmVjaXBlKHBhcmFtKTtcbiAgICAgIH0sIHRoaXMpO1xuICAgIH1cbiAgICByZXR1cm4gbmV3IHBleHBycy5BcHBseShydWxlTmFtZSwgb3B0UGFyYW1zKTtcbiAgfVxuXG4gIC8vIE5vdGUgdGhhdCB1bmxpa2Ugb3RoZXIgbWV0aG9kcyBpbiB0aGlzIGNsYXNzLCB0aGlzIG1ldGhvZCBjYW5ub3QgYmUgdXNlZCBhcyBhXG4gIC8vIGNvbnZlbmllbmNlIGNvbnN0cnVjdG9yLiBJdCBvbmx5IHdvcmtzIHdpdGggcmVjaXBlcywgYmVjYXVzZSBpdCByZWxpZXMgb25cbiAgLy8gYHRoaXMuY3VycmVudERlY2xgIGFuZCBgdGhpcy5jdXJyZW50UnVsZU5hbWVgIGJlaW5nIHNldC5cbiAgc3BsaWNlKGJlZm9yZVRlcm1zLCBhZnRlclRlcm1zKSB7XG4gICAgcmV0dXJuIG5ldyBwZXhwcnMuU3BsaWNlKFxuICAgICAgdGhpcy5jdXJyZW50RGVjbC5zdXBlckdyYW1tYXIsXG4gICAgICB0aGlzLmN1cnJlbnRSdWxlTmFtZSxcbiAgICAgIGJlZm9yZVRlcm1zLm1hcCh0ZXJtID0+IHRoaXMuZnJvbVJlY2lwZSh0ZXJtKSksXG4gICAgICBhZnRlclRlcm1zLm1hcCh0ZXJtID0+IHRoaXMuZnJvbVJlY2lwZSh0ZXJtKSlcbiAgICApO1xuICB9XG5cbiAgZnJvbVJlY2lwZShyZWNpcGUpIHtcbiAgICAvLyB0aGUgbWV0YS1pbmZvIG9mICdncmFtbWFyJyBpcyBwcm9jZXNzZWQgaW4gQnVpbGRlci5ncmFtbWFyXG4gICAgY29uc3QgYXJncyA9IHJlY2lwZVswXSA9PT0gJ2dyYW1tYXInID8gcmVjaXBlLnNsaWNlKDEpIDogcmVjaXBlLnNsaWNlKDIpO1xuICAgIGNvbnN0IHJlc3VsdCA9IHRoaXNbcmVjaXBlWzBdXSguLi5hcmdzKTtcblxuICAgIGNvbnN0IG1ldGFJbmZvID0gcmVjaXBlWzFdO1xuICAgIGlmIChtZXRhSW5mbykge1xuICAgICAgaWYgKG1ldGFJbmZvLnNvdXJjZUludGVydmFsICYmIHRoaXMuY3VycmVudERlY2wpIHtcbiAgICAgICAgcmVzdWx0LndpdGhTb3VyY2UodGhpcy5jdXJyZW50RGVjbC5zb3VyY2VJbnRlcnZhbCguLi5tZXRhSW5mby5zb3VyY2VJbnRlcnZhbCkpO1xuICAgICAgfVxuICAgIH1cbiAgICByZXR1cm4gcmVzdWx0O1xuICB9XG59XG4iLCJpbXBvcnQge0J1aWxkZXJ9IGZyb20gJy4vQnVpbGRlci5qcyc7XG5cbmV4cG9ydCBmdW5jdGlvbiBtYWtlUmVjaXBlKHJlY2lwZSkge1xuICBpZiAodHlwZW9mIHJlY2lwZSA9PT0gJ2Z1bmN0aW9uJykge1xuICAgIHJldHVybiByZWNpcGUuY2FsbChuZXcgQnVpbGRlcigpKTtcbiAgfSBlbHNlIHtcbiAgICBpZiAodHlwZW9mIHJlY2lwZSA9PT0gJ3N0cmluZycpIHtcbiAgICAgIC8vIHN0cmluZ2lmaWVkIEpTT04gcmVjaXBlXG4gICAgICByZWNpcGUgPSBKU09OLnBhcnNlKHJlY2lwZSk7XG4gICAgfVxuICAgIHJldHVybiBuZXcgQnVpbGRlcigpLmZyb21SZWNpcGUocmVjaXBlKTtcbiAgfVxufVxuIiwiaW1wb3J0IHttYWtlUmVjaXBlfSBmcm9tICcuLi9zcmMvbWFrZVJlY2lwZS5qcyc7XG5leHBvcnQgZGVmYXVsdCBtYWtlUmVjaXBlKFtcImdyYW1tYXJcIix7XCJzb3VyY2VcIjpcIkJ1aWx0SW5SdWxlcyB7XFxuXFxuICBhbG51bSAgKGFuIGFscGhhLW51bWVyaWMgY2hhcmFjdGVyKVxcbiAgICA9IGxldHRlclxcbiAgICB8IGRpZ2l0XFxuXFxuICBsZXR0ZXIgIChhIGxldHRlcilcXG4gICAgPSBsb3dlclxcbiAgICB8IHVwcGVyXFxuICAgIHwgdW5pY29kZUx0bW9cXG5cXG4gIGRpZ2l0ICAoYSBkaWdpdClcXG4gICAgPSBcXFwiMFxcXCIuLlxcXCI5XFxcIlxcblxcbiAgaGV4RGlnaXQgIChhIGhleGFkZWNpbWFsIGRpZ2l0KVxcbiAgICA9IGRpZ2l0XFxuICAgIHwgXFxcImFcXFwiLi5cXFwiZlxcXCJcXG4gICAgfCBcXFwiQVxcXCIuLlxcXCJGXFxcIlxcblxcbiAgTGlzdE9mPGVsZW0sIHNlcD5cXG4gICAgPSBOb25lbXB0eUxpc3RPZjxlbGVtLCBzZXA+XFxuICAgIHwgRW1wdHlMaXN0T2Y8ZWxlbSwgc2VwPlxcblxcbiAgTm9uZW1wdHlMaXN0T2Y8ZWxlbSwgc2VwPlxcbiAgICA9IGVsZW0gKHNlcCBlbGVtKSpcXG5cXG4gIEVtcHR5TGlzdE9mPGVsZW0sIHNlcD5cXG4gICAgPSAvKiBub3RoaW5nICovXFxuXFxuICBsaXN0T2Y8ZWxlbSwgc2VwPlxcbiAgICA9IG5vbmVtcHR5TGlzdE9mPGVsZW0sIHNlcD5cXG4gICAgfCBlbXB0eUxpc3RPZjxlbGVtLCBzZXA+XFxuXFxuICBub25lbXB0eUxpc3RPZjxlbGVtLCBzZXA+XFxuICAgID0gZWxlbSAoc2VwIGVsZW0pKlxcblxcbiAgZW1wdHlMaXN0T2Y8ZWxlbSwgc2VwPlxcbiAgICA9IC8qIG5vdGhpbmcgKi9cXG5cXG4gIC8vIEFsbG93cyBhIHN5bnRhY3RpYyBydWxlIGFwcGxpY2F0aW9uIHdpdGhpbiBhIGxleGljYWwgY29udGV4dC5cXG4gIGFwcGx5U3ludGFjdGljPGFwcD4gPSBhcHBcXG59XCJ9LFwiQnVpbHRJblJ1bGVzXCIsbnVsbCxudWxsLHtcImFsbnVtXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTgsNzhdfSxcImFuIGFscGhhLW51bWVyaWMgY2hhcmFjdGVyXCIsW10sW1wiYWx0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjAsNzhdfSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls2MCw2Nl19LFwibGV0dGVyXCIsW11dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzczLDc4XX0sXCJkaWdpdFwiLFtdXV1dLFwibGV0dGVyXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbODIsMTQyXX0sXCJhIGxldHRlclwiLFtdLFtcImFsdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEwNywxNDJdfSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMDcsMTEyXX0sXCJsb3dlclwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMTksMTI0XX0sXCJ1cHBlclwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMzEsMTQyXX0sXCJ1bmljb2RlTHRtb1wiLFtdXV1dLFwiZGlnaXRcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNDYsMTc3XX0sXCJhIGRpZ2l0XCIsW10sW1wicmFuZ2VcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNjksMTc3XX0sXCIwXCIsXCI5XCJdXSxcImhleERpZ2l0XCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTgxLDI1NF19LFwiYSBoZXhhZGVjaW1hbCBkaWdpdFwiLFtdLFtcImFsdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIxOSwyNTRdfSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyMTksMjI0XX0sXCJkaWdpdFwiLFtdXSxbXCJyYW5nZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzIzMSwyMzldfSxcImFcIixcImZcIl0sW1wicmFuZ2VcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNDYsMjU0XX0sXCJBXCIsXCJGXCJdXV0sXCJMaXN0T2ZcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNTgsMzM2XX0sbnVsbCxbXCJlbGVtXCIsXCJzZXBcIl0sW1wiYWx0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjgyLDMzNl19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzI4MiwzMDddfSxcIk5vbmVtcHR5TGlzdE9mXCIsW1tcInBhcmFtXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjk3LDMwMV19LDBdLFtcInBhcmFtXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzAzLDMwNl19LDFdXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzE0LDMzNl19LFwiRW1wdHlMaXN0T2ZcIixbW1wicGFyYW1cIix7XCJzb3VyY2VJbnRlcnZhbFwiOlszMjYsMzMwXX0sMF0sW1wicGFyYW1cIix7XCJzb3VyY2VJbnRlcnZhbFwiOlszMzIsMzM1XX0sMV1dXV1dLFwiTm9uZW1wdHlMaXN0T2ZcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlszNDAsMzg4XX0sbnVsbCxbXCJlbGVtXCIsXCJzZXBcIl0sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzcyLDM4OF19LFtcInBhcmFtXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzcyLDM3Nl19LDBdLFtcInN0YXJcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlszNzcsMzg4XX0sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzc4LDM4Nl19LFtcInBhcmFtXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzc4LDM4MV19LDFdLFtcInBhcmFtXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzgyLDM4Nl19LDBdXV1dXSxcIkVtcHR5TGlzdE9mXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzkyLDQzNF19LG51bGwsW1wiZWxlbVwiLFwic2VwXCJdLFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzQzOCw0MzhdfV1dLFwibGlzdE9mXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNDM4LDUxNl19LG51bGwsW1wiZWxlbVwiLFwic2VwXCJdLFtcImFsdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzQ2Miw1MTZdfSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls0NjIsNDg3XX0sXCJub25lbXB0eUxpc3RPZlwiLFtbXCJwYXJhbVwiLHtcInNvdXJjZUludGVydmFsXCI6WzQ3Nyw0ODFdfSwwXSxbXCJwYXJhbVwiLHtcInNvdXJjZUludGVydmFsXCI6WzQ4Myw0ODZdfSwxXV1dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzQ5NCw1MTZdfSxcImVtcHR5TGlzdE9mXCIsW1tcInBhcmFtXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNTA2LDUxMF19LDBdLFtcInBhcmFtXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNTEyLDUxNV19LDFdXV1dXSxcIm5vbmVtcHR5TGlzdE9mXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNTIwLDU2OF19LG51bGwsW1wiZWxlbVwiLFwic2VwXCJdLFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzU1Miw1NjhdfSxbXCJwYXJhbVwiLHtcInNvdXJjZUludGVydmFsXCI6WzU1Miw1NTZdfSwwXSxbXCJzdGFyXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNTU3LDU2OF19LFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzU1OCw1NjZdfSxbXCJwYXJhbVwiLHtcInNvdXJjZUludGVydmFsXCI6WzU1OCw1NjFdfSwxXSxbXCJwYXJhbVwiLHtcInNvdXJjZUludGVydmFsXCI6WzU2Miw1NjZdfSwwXV1dXV0sXCJlbXB0eUxpc3RPZlwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzU3Miw2ODJdfSxudWxsLFtcImVsZW1cIixcInNlcFwiXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls2ODUsNjg1XX1dXSxcImFwcGx5U3ludGFjdGljXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjg1LDcxMF19LG51bGwsW1wiYXBwXCJdLFtcInBhcmFtXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNzA3LDcxMF19LDBdXX1dKTtcbiIsImltcG9ydCBCdWlsdEluUnVsZXMgZnJvbSAnLi4vZGlzdC9idWlsdC1pbi1ydWxlcy5qcyc7XG5pbXBvcnQge0dyYW1tYXJ9IGZyb20gJy4vR3JhbW1hci5qcyc7XG5pbXBvcnQge2Fubm91bmNlQnVpbHRJblJ1bGVzfSBmcm9tICcuL3V0aWwuanMnO1xuXG5HcmFtbWFyLkJ1aWx0SW5SdWxlcyA9IEJ1aWx0SW5SdWxlcztcbmFubm91bmNlQnVpbHRJblJ1bGVzKEdyYW1tYXIuQnVpbHRJblJ1bGVzKTtcblxuLy8gRHVyaW5nIHRoZSBib290c3RyYXAgcHJvY2Vzcywgd2UgaW5zdGFudGlhdGUgc29tZSBncmFtbWFycyB0aGF0IHJlcXVpcmVcbi8vIHRoZSBidWlsdC1pbiBydWxlcyB0byBiZSBsb2FkZWQgZmlyc3QgKGUuZy4sIG9obS1ncmFtbWFyLm9obSkuIEJ5XG4vLyBleHBvcnRpbmcgYG1ha2VSZWNpcGVgIGhlcmUsIHRoZSByZWNpcGVzIGZvciB0aG9zZSBncmFtbWFycyBjYW4gZW5jb2RlXG4vLyB0aGF0IGRlcGVuZGVuY3kgYnkgaW1wb3J0aW5nIGl0IGZyb20gdGhpcyBtb2R1bGUuXG5leHBvcnQge21ha2VSZWNpcGV9IGZyb20gJy4vbWFrZVJlY2lwZS5qcyc7XG4iLCJpbXBvcnQge21ha2VSZWNpcGV9IGZyb20gJy4uL3NyYy9tYWluLWtlcm5lbC5qcyc7XG5leHBvcnQgZGVmYXVsdCBtYWtlUmVjaXBlKFtcImdyYW1tYXJcIix7XCJzb3VyY2VcIjpcIk9obSB7XFxuXFxuICBHcmFtbWFyc1xcbiAgICA9IEdyYW1tYXIqXFxuXFxuICBHcmFtbWFyXFxuICAgID0gaWRlbnQgU3VwZXJHcmFtbWFyPyBcXFwie1xcXCIgUnVsZSogXFxcIn1cXFwiXFxuXFxuICBTdXBlckdyYW1tYXJcXG4gICAgPSBcXFwiPDpcXFwiIGlkZW50XFxuXFxuICBSdWxlXFxuICAgID0gaWRlbnQgRm9ybWFscz8gcnVsZURlc2NyPyBcXFwiPVxcXCIgIFJ1bGVCb2R5ICAtLSBkZWZpbmVcXG4gICAgfCBpZGVudCBGb3JtYWxzPyAgICAgICAgICAgIFxcXCI6PVxcXCIgT3ZlcnJpZGVSdWxlQm9keSAgLS0gb3ZlcnJpZGVcXG4gICAgfCBpZGVudCBGb3JtYWxzPyAgICAgICAgICAgIFxcXCIrPVxcXCIgUnVsZUJvZHkgIC0tIGV4dGVuZFxcblxcbiAgUnVsZUJvZHlcXG4gICAgPSBcXFwifFxcXCI/IE5vbmVtcHR5TGlzdE9mPFRvcExldmVsVGVybSwgXFxcInxcXFwiPlxcblxcbiAgVG9wTGV2ZWxUZXJtXFxuICAgID0gU2VxIGNhc2VOYW1lICAtLSBpbmxpbmVcXG4gICAgfCBTZXFcXG5cXG4gIE92ZXJyaWRlUnVsZUJvZHlcXG4gICAgPSBcXFwifFxcXCI/IE5vbmVtcHR5TGlzdE9mPE92ZXJyaWRlVG9wTGV2ZWxUZXJtLCBcXFwifFxcXCI+XFxuXFxuICBPdmVycmlkZVRvcExldmVsVGVybVxcbiAgICA9IFxcXCIuLi5cXFwiICAtLSBzdXBlclNwbGljZVxcbiAgICB8IFRvcExldmVsVGVybVxcblxcbiAgRm9ybWFsc1xcbiAgICA9IFxcXCI8XFxcIiBMaXN0T2Y8aWRlbnQsIFxcXCIsXFxcIj4gXFxcIj5cXFwiXFxuXFxuICBQYXJhbXNcXG4gICAgPSBcXFwiPFxcXCIgTGlzdE9mPFNlcSwgXFxcIixcXFwiPiBcXFwiPlxcXCJcXG5cXG4gIEFsdFxcbiAgICA9IE5vbmVtcHR5TGlzdE9mPFNlcSwgXFxcInxcXFwiPlxcblxcbiAgU2VxXFxuICAgID0gSXRlcipcXG5cXG4gIEl0ZXJcXG4gICAgPSBQcmVkIFxcXCIqXFxcIiAgLS0gc3RhclxcbiAgICB8IFByZWQgXFxcIitcXFwiICAtLSBwbHVzXFxuICAgIHwgUHJlZCBcXFwiP1xcXCIgIC0tIG9wdFxcbiAgICB8IFByZWRcXG5cXG4gIFByZWRcXG4gICAgPSBcXFwiflxcXCIgTGV4ICAtLSBub3RcXG4gICAgfCBcXFwiJlxcXCIgTGV4ICAtLSBsb29rYWhlYWRcXG4gICAgfCBMZXhcXG5cXG4gIExleFxcbiAgICA9IFxcXCIjXFxcIiBCYXNlICAtLSBsZXhcXG4gICAgfCBCYXNlXFxuXFxuICBCYXNlXFxuICAgID0gaWRlbnQgUGFyYW1zPyB+KHJ1bGVEZXNjcj8gXFxcIj1cXFwiIHwgXFxcIjo9XFxcIiB8IFxcXCIrPVxcXCIpICAtLSBhcHBsaWNhdGlvblxcbiAgICB8IG9uZUNoYXJUZXJtaW5hbCBcXFwiLi5cXFwiIG9uZUNoYXJUZXJtaW5hbCAgICAgICAgICAgLS0gcmFuZ2VcXG4gICAgfCB0ZXJtaW5hbCAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIC0tIHRlcm1pbmFsXFxuICAgIHwgXFxcIihcXFwiIEFsdCBcXFwiKVxcXCIgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAtLSBwYXJlblxcblxcbiAgcnVsZURlc2NyICAoYSBydWxlIGRlc2NyaXB0aW9uKVxcbiAgICA9IFxcXCIoXFxcIiBydWxlRGVzY3JUZXh0IFxcXCIpXFxcIlxcblxcbiAgcnVsZURlc2NyVGV4dFxcbiAgICA9ICh+XFxcIilcXFwiIGFueSkqXFxuXFxuICBjYXNlTmFtZVxcbiAgICA9IFxcXCItLVxcXCIgKH5cXFwiXFxcXG5cXFwiIHNwYWNlKSogbmFtZSAoflxcXCJcXFxcblxcXCIgc3BhY2UpKiAoXFxcIlxcXFxuXFxcIiB8ICZcXFwifVxcXCIpXFxuXFxuICBuYW1lICAoYSBuYW1lKVxcbiAgICA9IG5hbWVGaXJzdCBuYW1lUmVzdCpcXG5cXG4gIG5hbWVGaXJzdFxcbiAgICA9IFxcXCJfXFxcIlxcbiAgICB8IGxldHRlclxcblxcbiAgbmFtZVJlc3RcXG4gICAgPSBcXFwiX1xcXCJcXG4gICAgfCBhbG51bVxcblxcbiAgaWRlbnQgIChhbiBpZGVudGlmaWVyKVxcbiAgICA9IG5hbWVcXG5cXG4gIHRlcm1pbmFsXFxuICAgID0gXFxcIlxcXFxcXFwiXFxcIiB0ZXJtaW5hbENoYXIqIFxcXCJcXFxcXFxcIlxcXCJcXG5cXG4gIG9uZUNoYXJUZXJtaW5hbFxcbiAgICA9IFxcXCJcXFxcXFxcIlxcXCIgdGVybWluYWxDaGFyIFxcXCJcXFxcXFxcIlxcXCJcXG5cXG4gIHRlcm1pbmFsQ2hhclxcbiAgICA9IGVzY2FwZUNoYXJcXG4gICAgICB8IH5cXFwiXFxcXFxcXFxcXFwiIH5cXFwiXFxcXFxcXCJcXFwiIH5cXFwiXFxcXG5cXFwiIFxcXCJcXFxcdXswfVxcXCIuLlxcXCJcXFxcdXsxMEZGRkZ9XFxcIlxcblxcbiAgZXNjYXBlQ2hhciAgKGFuIGVzY2FwZSBzZXF1ZW5jZSlcXG4gICAgPSBcXFwiXFxcXFxcXFxcXFxcXFxcXFxcXCIgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgLS0gYmFja3NsYXNoXFxuICAgIHwgXFxcIlxcXFxcXFxcXFxcXFxcXCJcXFwiICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIC0tIGRvdWJsZVF1b3RlXFxuICAgIHwgXFxcIlxcXFxcXFxcXFxcXCdcXFwiICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIC0tIHNpbmdsZVF1b3RlXFxuICAgIHwgXFxcIlxcXFxcXFxcYlxcXCIgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIC0tIGJhY2tzcGFjZVxcbiAgICB8IFxcXCJcXFxcXFxcXG5cXFwiICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAtLSBsaW5lRmVlZFxcbiAgICB8IFxcXCJcXFxcXFxcXHJcXFwiICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAtLSBjYXJyaWFnZVJldHVyblxcbiAgICB8IFxcXCJcXFxcXFxcXHRcXFwiICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAtLSB0YWJcXG4gICAgfCBcXFwiXFxcXFxcXFx1e1xcXCIgaGV4RGlnaXQgaGV4RGlnaXQ/IGhleERpZ2l0P1xcbiAgICAgICAgICAgICBoZXhEaWdpdD8gaGV4RGlnaXQ/IGhleERpZ2l0PyBcXFwifVxcXCIgICAtLSB1bmljb2RlQ29kZVBvaW50XFxuICAgIHwgXFxcIlxcXFxcXFxcdVxcXCIgaGV4RGlnaXQgaGV4RGlnaXQgaGV4RGlnaXQgaGV4RGlnaXQgIC0tIHVuaWNvZGVFc2NhcGVcXG4gICAgfCBcXFwiXFxcXFxcXFx4XFxcIiBoZXhEaWdpdCBoZXhEaWdpdCAgICAgICAgICAgICAgICAgICAgLS0gaGV4RXNjYXBlXFxuXFxuICBzcGFjZVxcbiAgICs9IGNvbW1lbnRcXG5cXG4gIGNvbW1lbnRcXG4gICAgPSBcXFwiLy9cXFwiICh+XFxcIlxcXFxuXFxcIiBhbnkpKiAmKFxcXCJcXFxcblxcXCIgfCBlbmQpICAtLSBzaW5nbGVMaW5lXFxuICAgIHwgXFxcIi8qXFxcIiAoflxcXCIqL1xcXCIgYW55KSogXFxcIiovXFxcIiAgLS0gbXVsdGlMaW5lXFxuXFxuICB0b2tlbnMgPSB0b2tlbipcXG5cXG4gIHRva2VuID0gY2FzZU5hbWUgfCBjb21tZW50IHwgaWRlbnQgfCBvcGVyYXRvciB8IHB1bmN0dWF0aW9uIHwgdGVybWluYWwgfCBhbnlcXG5cXG4gIG9wZXJhdG9yID0gXFxcIjw6XFxcIiB8IFxcXCI9XFxcIiB8IFxcXCI6PVxcXCIgfCBcXFwiKz1cXFwiIHwgXFxcIipcXFwiIHwgXFxcIitcXFwiIHwgXFxcIj9cXFwiIHwgXFxcIn5cXFwiIHwgXFxcIiZcXFwiXFxuXFxuICBwdW5jdHVhdGlvbiA9IFxcXCI8XFxcIiB8IFxcXCI+XFxcIiB8IFxcXCIsXFxcIiB8IFxcXCItLVxcXCJcXG59XCJ9LFwiT2htXCIsbnVsbCxcIkdyYW1tYXJzXCIse1wiR3JhbW1hcnNcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls5LDMyXX0sbnVsbCxbXSxbXCJzdGFyXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjQsMzJdfSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNCwzMV19LFwiR3JhbW1hclwiLFtdXV1dLFwiR3JhbW1hclwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzM2LDgzXX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls1MCw4M119LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzUwLDU1XX0sXCJpZGVudFwiLFtdXSxbXCJvcHRcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls1Niw2OV19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzU2LDY4XX0sXCJTdXBlckdyYW1tYXJcIixbXV1dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNzAsNzNdfSxcIntcIl0sW1wic3RhclwiLHtcInNvdXJjZUludGVydmFsXCI6Wzc0LDc5XX0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNzQsNzhdfSxcIlJ1bGVcIixbXV1dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbODAsODNdfSxcIn1cIl1dXSxcIlN1cGVyR3JhbW1hclwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6Wzg3LDExNl19LG51bGwsW10sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTA2LDExNl19LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTA2LDExMF19LFwiPDpcIl0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTExLDExNl19LFwiaWRlbnRcIixbXV1dXSxcIlJ1bGVfZGVmaW5lXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTMxLDE4MV19LG51bGwsW10sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTMxLDE3MF19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEzMSwxMzZdfSxcImlkZW50XCIsW11dLFtcIm9wdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEzNywxNDVdfSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMzcsMTQ0XX0sXCJGb3JtYWxzXCIsW11dXSxbXCJvcHRcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNDYsMTU2XX0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTQ2LDE1NV19LFwicnVsZURlc2NyXCIsW11dXSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE1NywxNjBdfSxcIj1cIl0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTYyLDE3MF19LFwiUnVsZUJvZHlcIixbXV1dXSxcIlJ1bGVfb3ZlcnJpZGVcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxODgsMjQ4XX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxODgsMjM1XX0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTg4LDE5M119LFwiaWRlbnRcIixbXV0sW1wib3B0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTk0LDIwMl19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE5NCwyMDFdfSxcIkZvcm1hbHNcIixbXV1dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjE0LDIxOF19LFwiOj1cIl0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjE5LDIzNV19LFwiT3ZlcnJpZGVSdWxlQm9keVwiLFtdXV1dLFwiUnVsZV9leHRlbmRcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNTUsMzA1XX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNTUsMjk0XX0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjU1LDI2MF19LFwiaWRlbnRcIixbXV0sW1wib3B0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjYxLDI2OV19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzI2MSwyNjhdfSxcIkZvcm1hbHNcIixbXV1dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjgxLDI4NV19LFwiKz1cIl0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjg2LDI5NF19LFwiUnVsZUJvZHlcIixbXV1dXSxcIlJ1bGVcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMjAsMzA1XX0sbnVsbCxbXSxbXCJhbHRcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMzEsMzA1XX0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTMxLDE3MF19LFwiUnVsZV9kZWZpbmVcIixbXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTg4LDIzNV19LFwiUnVsZV9vdmVycmlkZVwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNTUsMjk0XX0sXCJSdWxlX2V4dGVuZFwiLFtdXV1dLFwiUnVsZUJvZHlcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlszMDksMzYyXX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlszMjQsMzYyXX0sW1wib3B0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzI0LDMyOF19LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzI0LDMyN119LFwifFwiXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzI5LDM2Ml19LFwiTm9uZW1wdHlMaXN0T2ZcIixbW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzQ0LDM1Nl19LFwiVG9wTGV2ZWxUZXJtXCIsW11dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzU4LDM2MV19LFwifFwiXV1dXV0sXCJUb3BMZXZlbFRlcm1faW5saW5lXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzg1LDQwOF19LG51bGwsW10sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzg1LDM5N119LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzM4NSwzODhdfSxcIlNlcVwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlszODksMzk3XX0sXCJjYXNlTmFtZVwiLFtdXV1dLFwiVG9wTGV2ZWxUZXJtXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzY2LDQxOF19LG51bGwsW10sW1wiYWx0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbMzg1LDQxOF19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzM4NSwzOTddfSxcIlRvcExldmVsVGVybV9pbmxpbmVcIixbXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNDE1LDQxOF19LFwiU2VxXCIsW11dXV0sXCJPdmVycmlkZVJ1bGVCb2R5XCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNDIyLDQ5MV19LG51bGwsW10sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNDQ1LDQ5MV19LFtcIm9wdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzQ0NSw0NDldfSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzQ0NSw0NDhdfSxcInxcIl1dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzQ1MCw0OTFdfSxcIk5vbmVtcHR5TGlzdE9mXCIsW1tcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzQ2NSw0ODVdfSxcIk92ZXJyaWRlVG9wTGV2ZWxUZXJtXCIsW11dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNDg3LDQ5MF19LFwifFwiXV1dXV0sXCJPdmVycmlkZVRvcExldmVsVGVybV9zdXBlclNwbGljZVwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzUyMiw1NDNdfSxudWxsLFtdLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNTIyLDUyN119LFwiLi4uXCJdXSxcIk92ZXJyaWRlVG9wTGV2ZWxUZXJtXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNDk1LDU2Ml19LG51bGwsW10sW1wiYWx0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbNTIyLDU2Ml19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzUyMiw1MjddfSxcIk92ZXJyaWRlVG9wTGV2ZWxUZXJtX3N1cGVyU3BsaWNlXCIsW11dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzU1MCw1NjJdfSxcIlRvcExldmVsVGVybVwiLFtdXV1dLFwiRm9ybWFsc1wiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzU2Niw2MDZdfSxudWxsLFtdLFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzU4MCw2MDZdfSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzU4MCw1ODNdfSxcIjxcIl0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNTg0LDYwMl19LFwiTGlzdE9mXCIsW1tcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzU5MSw1OTZdfSxcImlkZW50XCIsW11dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNTk4LDYwMV19LFwiLFwiXV1dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjAzLDYwNl19LFwiPlwiXV1dLFwiUGFyYW1zXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjEwLDY0N119LG51bGwsW10sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjIzLDY0N119LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjIzLDYyNl19LFwiPFwiXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls2MjcsNjQzXX0sXCJMaXN0T2ZcIixbW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjM0LDYzN119LFwiU2VxXCIsW11dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjM5LDY0Ml19LFwiLFwiXV1dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjQ0LDY0N119LFwiPlwiXV1dLFwiQWx0XCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjUxLDY4NV19LG51bGwsW10sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjYxLDY4NV19LFwiTm9uZW1wdHlMaXN0T2ZcIixbW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjc2LDY3OV19LFwiU2VxXCIsW11dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjgxLDY4NF19LFwifFwiXV1dXSxcIlNlcVwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzY4OSw3MDRdfSxudWxsLFtdLFtcInN0YXJcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls2OTksNzA0XX0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNjk5LDcwM119LFwiSXRlclwiLFtdXV1dLFwiSXRlcl9zdGFyXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNzE5LDczNl19LG51bGwsW10sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNzE5LDcyN119LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzcxOSw3MjNdfSxcIlByZWRcIixbXV0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls3MjQsNzI3XX0sXCIqXCJdXV0sXCJJdGVyX3BsdXNcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls3NDMsNzYwXX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls3NDMsNzUxXX0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNzQzLDc0N119LFwiUHJlZFwiLFtdXSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6Wzc0OCw3NTFdfSxcIitcIl1dXSxcIkl0ZXJfb3B0XCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNzY3LDc4M119LG51bGwsW10sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNzY3LDc3NV19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6Wzc2Nyw3NzFdfSxcIlByZWRcIixbXV0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls3NzIsNzc1XX0sXCI/XCJdXV0sXCJJdGVyXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNzA4LDc5NF19LG51bGwsW10sW1wiYWx0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbNzE5LDc5NF19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzcxOSw3MjddfSxcIkl0ZXJfc3RhclwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls3NDMsNzUxXX0sXCJJdGVyX3BsdXNcIixbXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNzY3LDc3NV19LFwiSXRlcl9vcHRcIixbXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbNzkwLDc5NF19LFwiUHJlZFwiLFtdXV1dLFwiUHJlZF9ub3RcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4MDksODI0XX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4MDksODE2XX0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4MDksODEyXX0sXCJ+XCJdLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzgxMyw4MTZdfSxcIkxleFwiLFtdXV1dLFwiUHJlZF9sb29rYWhlYWRcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4MzEsODUyXX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4MzEsODM4XX0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4MzEsODM0XX0sXCImXCJdLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzgzNSw4MzhdfSxcIkxleFwiLFtdXV1dLFwiUHJlZFwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6Wzc5OCw4NjJdfSxudWxsLFtdLFtcImFsdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzgwOSw4NjJdfSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4MDksODE2XX0sXCJQcmVkX25vdFwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4MzEsODM4XX0sXCJQcmVkX2xvb2thaGVhZFwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4NTksODYyXX0sXCJMZXhcIixbXV1dXSxcIkxleF9sZXhcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4NzYsODkyXX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4NzYsODg0XX0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4NzYsODc5XX0sXCIjXCJdLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6Wzg4MCw4ODRdfSxcIkJhc2VcIixbXV1dXSxcIkxleFwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6Wzg2Niw5MDNdfSxudWxsLFtdLFtcImFsdFwiLHtcInNvdXJjZUludGVydmFsXCI6Wzg3Niw5MDNdfSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls4NzYsODg0XX0sXCJMZXhfbGV4XCIsW11dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6Wzg5OSw5MDNdfSxcIkJhc2VcIixbXV1dXSxcIkJhc2VfYXBwbGljYXRpb25cIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls5MTgsOTc5XX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls5MTgsOTYzXX0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbOTE4LDkyM119LFwiaWRlbnRcIixbXV0sW1wib3B0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbOTI0LDkzMV19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzkyNCw5MzBdfSxcIlBhcmFtc1wiLFtdXV0sW1wibm90XCIse1wic291cmNlSW50ZXJ2YWxcIjpbOTMyLDk2M119LFtcImFsdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzkzNCw5NjJdfSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls5MzQsOTQ4XX0sW1wib3B0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbOTM0LDk0NF19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzkzNCw5NDNdfSxcInJ1bGVEZXNjclwiLFtdXV0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls5NDUsOTQ4XX0sXCI9XCJdXSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6Wzk1MSw5NTVdfSxcIjo9XCJdLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbOTU4LDk2Ml19LFwiKz1cIl1dXV1dLFwiQmFzZV9yYW5nZVwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6Wzk4NiwxMDQxXX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls5ODYsMTAyMl19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6Wzk4NiwxMDAxXX0sXCJvbmVDaGFyVGVybWluYWxcIixbXV0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMDAyLDEwMDZdfSxcIi4uXCJdLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEwMDcsMTAyMl19LFwib25lQ2hhclRlcm1pbmFsXCIsW11dXV0sXCJCYXNlX3Rlcm1pbmFsXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTA0OCwxMTA2XX0sbnVsbCxbXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMDQ4LDEwNTZdfSxcInRlcm1pbmFsXCIsW11dXSxcIkJhc2VfcGFyZW5cIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMTEzLDExNjhdfSxudWxsLFtdLFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzExMTMsMTEyNF19LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTExMywxMTE2XX0sXCIoXCJdLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzExMTcsMTEyMF19LFwiQWx0XCIsW11dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTEyMSwxMTI0XX0sXCIpXCJdXV0sXCJCYXNlXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbOTA3LDExNjhdfSxudWxsLFtdLFtcImFsdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzkxOCwxMTY4XX0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbOTE4LDk2M119LFwiQmFzZV9hcHBsaWNhdGlvblwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls5ODYsMTAyMl19LFwiQmFzZV9yYW5nZVwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMDQ4LDEwNTZdfSxcIkJhc2VfdGVybWluYWxcIixbXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTExMywxMTI0XX0sXCJCYXNlX3BhcmVuXCIsW11dXV0sXCJydWxlRGVzY3JcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMTcyLDEyMzFdfSxcImEgcnVsZSBkZXNjcmlwdGlvblwiLFtdLFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyMTAsMTIzMV19LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTIxMCwxMjEzXX0sXCIoXCJdLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyMTQsMTIyN119LFwicnVsZURlc2NyVGV4dFwiLFtdXSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyMjgsMTIzMV19LFwiKVwiXV1dLFwicnVsZURlc2NyVGV4dFwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyMzUsMTI2Nl19LG51bGwsW10sW1wic3RhclwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyNTUsMTI2Nl19LFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyNTYsMTI2NF19LFtcIm5vdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyNTYsMTI2MF19LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTI1NywxMjYwXX0sXCIpXCJdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMjYxLDEyNjRdfSxcImFueVwiLFtdXV1dXSxcImNhc2VOYW1lXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTI3MCwxMzM4XX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMjg1LDEzMzhdfSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyODUsMTI4OV19LFwiLS1cIl0sW1wic3RhclwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyOTAsMTMwNF19LFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyOTEsMTMwMl19LFtcIm5vdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyOTEsMTI5Nl19LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTI5MiwxMjk2XX0sXCJcXG5cIl1dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyOTcsMTMwMl19LFwic3BhY2VcIixbXV1dXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMzA1LDEzMDldfSxcIm5hbWVcIixbXV0sW1wic3RhclwiLHtcInNvdXJjZUludGVydmFsXCI6WzEzMTAsMTMyNF19LFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzEzMTEsMTMyMl19LFtcIm5vdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEzMTEsMTMxNl19LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTMxMiwxMzE2XX0sXCJcXG5cIl1dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEzMTcsMTMyMl19LFwic3BhY2VcIixbXV1dXSxbXCJhbHRcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMzI2LDEzMzddfSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEzMjYsMTMzMF19LFwiXFxuXCJdLFtcImxvb2thaGVhZFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEzMzMsMTMzN119LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTMzNCwxMzM3XX0sXCJ9XCJdXV1dXSxcIm5hbWVcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMzQyLDEzODJdfSxcImEgbmFtZVwiLFtdLFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzEzNjMsMTM4Ml19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEzNjMsMTM3Ml19LFwibmFtZUZpcnN0XCIsW11dLFtcInN0YXJcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMzczLDEzODJdfSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMzczLDEzODFdfSxcIm5hbWVSZXN0XCIsW11dXV1dLFwibmFtZUZpcnN0XCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTM4NiwxNDE4XX0sbnVsbCxbXSxbXCJhbHRcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNDAyLDE0MThdfSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE0MDIsMTQwNV19LFwiX1wiXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNDEyLDE0MThdfSxcImxldHRlclwiLFtdXV1dLFwibmFtZVJlc3RcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNDIyLDE0NTJdfSxudWxsLFtdLFtcImFsdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE0MzcsMTQ1Ml19LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTQzNywxNDQwXX0sXCJfXCJdLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE0NDcsMTQ1Ml19LFwiYWxudW1cIixbXV1dXSxcImlkZW50XCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTQ1NiwxNDg5XX0sXCJhbiBpZGVudGlmaWVyXCIsW10sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTQ4NSwxNDg5XX0sXCJuYW1lXCIsW11dXSxcInRlcm1pbmFsXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTQ5MywxNTMxXX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNTA4LDE1MzFdfSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE1MDgsMTUxMl19LFwiXFxcIlwiXSxbXCJzdGFyXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTUxMywxNTI2XX0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTUxMywxNTI1XX0sXCJ0ZXJtaW5hbENoYXJcIixbXV1dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTUyNywxNTMxXX0sXCJcXFwiXCJdXV0sXCJvbmVDaGFyVGVybWluYWxcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNTM1LDE1NzldfSxudWxsLFtdLFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzE1NTcsMTU3OV19LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTU1NywxNTYxXX0sXCJcXFwiXCJdLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE1NjIsMTU3NF19LFwidGVybWluYWxDaGFyXCIsW11dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTU3NSwxNTc5XX0sXCJcXFwiXCJdXV0sXCJ0ZXJtaW5hbENoYXJcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNTgzLDE2NjBdfSxudWxsLFtdLFtcImFsdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE2MDIsMTY2MF19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE2MDIsMTYxMl19LFwiZXNjYXBlQ2hhclwiLFtdXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNjIxLDE2NjBdfSxbXCJub3RcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNjIxLDE2MjZdfSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE2MjIsMTYyNl19LFwiXFxcXFwiXV0sW1wibm90XCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTYyNywxNjMyXX0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNjI4LDE2MzJdfSxcIlxcXCJcIl1dLFtcIm5vdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE2MzMsMTYzOF19LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTYzNCwxNjM4XX0sXCJcXG5cIl1dLFtcInJhbmdlXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTYzOSwxNjYwXX0sXCJcXHUwMDAwXCIsXCL0j7+/XCJdXV1dLFwiZXNjYXBlQ2hhcl9iYWNrc2xhc2hcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNzAzLDE3NThdfSxudWxsLFtdLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTcwMywxNzA5XX0sXCJcXFxcXFxcXFwiXV0sXCJlc2NhcGVDaGFyX2RvdWJsZVF1b3RlXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTc2NSwxODIyXX0sbnVsbCxbXSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE3NjUsMTc3MV19LFwiXFxcXFxcXCJcIl1dLFwiZXNjYXBlQ2hhcl9zaW5nbGVRdW90ZVwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzE4MjksMTg4Nl19LG51bGwsW10sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxODI5LDE4MzVdfSxcIlxcXFwnXCJdXSxcImVzY2FwZUNoYXJfYmFja3NwYWNlXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTg5MywxOTQ4XX0sbnVsbCxbXSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE4OTMsMTg5OF19LFwiXFxcXGJcIl1dLFwiZXNjYXBlQ2hhcl9saW5lRmVlZFwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzE5NTUsMjAwOV19LG51bGwsW10sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxOTU1LDE5NjBdfSxcIlxcXFxuXCJdXSxcImVzY2FwZUNoYXJfY2FycmlhZ2VSZXR1cm5cIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyMDE2LDIwNzZdfSxudWxsLFtdLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjAxNiwyMDIxXX0sXCJcXFxcclwiXV0sXCJlc2NhcGVDaGFyX3RhYlwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzIwODMsMjEzMl19LG51bGwsW10sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyMDgzLDIwODhdfSxcIlxcXFx0XCJdXSxcImVzY2FwZUNoYXJfdW5pY29kZUNvZGVQb2ludFwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzIxMzksMjI0M119LG51bGwsW10sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjEzOSwyMjIxXX0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyMTM5LDIxNDVdfSxcIlxcXFx1e1wiXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyMTQ2LDIxNTRdfSxcImhleERpZ2l0XCIsW11dLFtcIm9wdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIxNTUsMjE2NF19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIxNTUsMjE2M119LFwiaGV4RGlnaXRcIixbXV1dLFtcIm9wdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIxNjUsMjE3NF19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIxNjUsMjE3M119LFwiaGV4RGlnaXRcIixbXV1dLFtcIm9wdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIxODgsMjE5N119LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIxODgsMjE5Nl19LFwiaGV4RGlnaXRcIixbXV1dLFtcIm9wdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIxOTgsMjIwN119LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIxOTgsMjIwNl19LFwiaGV4RGlnaXRcIixbXV1dLFtcIm9wdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIyMDgsMjIxN119LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIyMDgsMjIxNl19LFwiaGV4RGlnaXRcIixbXV1dLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjIxOCwyMjIxXX0sXCJ9XCJdXV0sXCJlc2NhcGVDaGFyX3VuaWNvZGVFc2NhcGVcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyMjUwLDIzMDldfSxudWxsLFtdLFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzIyNTAsMjI5MV19LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjI1MCwyMjU1XX0sXCJcXFxcdVwiXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyMjU2LDIyNjRdfSxcImhleERpZ2l0XCIsW11dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIyNjUsMjI3M119LFwiaGV4RGlnaXRcIixbXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjI3NCwyMjgyXX0sXCJoZXhEaWdpdFwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyMjgzLDIyOTFdfSxcImhleERpZ2l0XCIsW11dXV0sXCJlc2NhcGVDaGFyX2hleEVzY2FwZVwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzIzMTYsMjM3MV19LG51bGwsW10sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjMxNiwyMzM5XX0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyMzE2LDIzMjFdfSxcIlxcXFx4XCJdLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIzMjIsMjMzMF19LFwiaGV4RGlnaXRcIixbXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjMzMSwyMzM5XX0sXCJoZXhEaWdpdFwiLFtdXV1dLFwiZXNjYXBlQ2hhclwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzE2NjQsMjM3MV19LFwiYW4gZXNjYXBlIHNlcXVlbmNlXCIsW10sW1wiYWx0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTcwMywyMzcxXX0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTcwMywxNzA5XX0sXCJlc2NhcGVDaGFyX2JhY2tzbGFzaFwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNzY1LDE3NzFdfSxcImVzY2FwZUNoYXJfZG91YmxlUXVvdGVcIixbXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTgyOSwxODM1XX0sXCJlc2NhcGVDaGFyX3NpbmdsZVF1b3RlXCIsW11dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE4OTMsMTg5OF19LFwiZXNjYXBlQ2hhcl9iYWNrc3BhY2VcIixbXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTk1NSwxOTYwXX0sXCJlc2NhcGVDaGFyX2xpbmVGZWVkXCIsW11dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIwMTYsMjAyMV19LFwiZXNjYXBlQ2hhcl9jYXJyaWFnZVJldHVyblwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyMDgzLDIwODhdfSxcImVzY2FwZUNoYXJfdGFiXCIsW11dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIxMzksMjIyMV19LFwiZXNjYXBlQ2hhcl91bmljb2RlQ29kZVBvaW50XCIsW11dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIyNTAsMjI5MV19LFwiZXNjYXBlQ2hhcl91bmljb2RlRXNjYXBlXCIsW11dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzIzMTYsMjMzOV19LFwiZXNjYXBlQ2hhcl9oZXhFc2NhcGVcIixbXV1dXSxcInNwYWNlXCI6W1wiZXh0ZW5kXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjM3NSwyMzk0XX0sbnVsbCxbXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyMzg3LDIzOTRdfSxcImNvbW1lbnRcIixbXV1dLFwiY29tbWVudF9zaW5nbGVMaW5lXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjQxMiwyNDU4XX0sbnVsbCxbXSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNDEyLDI0NDNdfSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzI0MTIsMjQxNl19LFwiLy9cIl0sW1wic3RhclwiLHtcInNvdXJjZUludGVydmFsXCI6WzI0MTcsMjQyOV19LFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzI0MTgsMjQyN119LFtcIm5vdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzI0MTgsMjQyM119LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjQxOSwyNDIzXX0sXCJcXG5cIl1dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzI0MjQsMjQyN119LFwiYW55XCIsW11dXV0sW1wibG9va2FoZWFkXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjQzMCwyNDQzXX0sW1wiYWx0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjQzMiwyNDQyXX0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNDMyLDI0MzZdfSxcIlxcblwiXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNDM5LDI0NDJdfSxcImVuZFwiLFtdXV1dXV0sXCJjb21tZW50X211bHRpTGluZVwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzI0NjUsMjUwMV19LG51bGwsW10sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjQ2NSwyNDg3XX0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNDY1LDI0NjldfSxcIi8qXCJdLFtcInN0YXJcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNDcwLDI0ODJdfSxbXCJzZXFcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNDcxLDI0ODBdfSxbXCJub3RcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNDcxLDI0NzZdfSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzI0NzIsMjQ3Nl19LFwiKi9cIl1dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzI0NzcsMjQ4MF19LFwiYW55XCIsW11dXV0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNDgzLDI0ODddfSxcIiovXCJdXV0sXCJjb21tZW50XCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjM5OCwyNTAxXX0sbnVsbCxbXSxbXCJhbHRcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNDEyLDI1MDFdfSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNDEyLDI0NDNdfSxcImNvbW1lbnRfc2luZ2xlTGluZVwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNDY1LDI0ODddfSxcImNvbW1lbnRfbXVsdGlMaW5lXCIsW11dXV0sXCJ0b2tlbnNcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNTA1LDI1MjBdfSxudWxsLFtdLFtcInN0YXJcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNTE0LDI1MjBdfSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNTE0LDI1MTldfSxcInRva2VuXCIsW11dXV0sXCJ0b2tlblwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzI1MjQsMjYwMF19LG51bGwsW10sW1wiYWx0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjUzMiwyNjAwXX0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjUzMiwyNTQwXX0sXCJjYXNlTmFtZVwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNTQzLDI1NTBdfSxcImNvbW1lbnRcIixbXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjU1MywyNTU4XX0sXCJpZGVudFwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNTYxLDI1NjldfSxcIm9wZXJhdG9yXCIsW11dLFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzI1NzIsMjU4M119LFwicHVuY3R1YXRpb25cIixbXV0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjU4NiwyNTk0XX0sXCJ0ZXJtaW5hbFwiLFtdXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNTk3LDI2MDBdfSxcImFueVwiLFtdXV1dLFwib3BlcmF0b3JcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNjA0LDI2NjldfSxudWxsLFtdLFtcImFsdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzI2MTUsMjY2OV19LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjYxNSwyNjE5XX0sXCI8OlwiXSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzI2MjIsMjYyNV19LFwiPVwiXSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzI2MjgsMjYzMl19LFwiOj1cIl0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNjM1LDI2MzldfSxcIis9XCJdLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjY0MiwyNjQ1XX0sXCIqXCJdLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjY0OCwyNjUxXX0sXCIrXCJdLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjY1NCwyNjU3XX0sXCI/XCJdLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjY2MCwyNjYzXX0sXCJ+XCJdLFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjY2NiwyNjY5XX0sXCImXCJdXV0sXCJwdW5jdHVhdGlvblwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzI2NzMsMjcwOV19LG51bGwsW10sW1wiYWx0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjY4NywyNzA5XX0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNjg3LDI2OTBdfSxcIjxcIl0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNjkzLDI2OTZdfSxcIj5cIl0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNjk5LDI3MDJdfSxcIixcIl0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNzA1LDI3MDldfSxcIi0tXCJdXV19XSk7XG4iLCJpbXBvcnQgb2htR3JhbW1hciBmcm9tICcuLi9kaXN0L29obS1ncmFtbWFyLmpzJztcbmltcG9ydCB7QnVpbGRlcn0gZnJvbSAnLi9CdWlsZGVyLmpzJztcbmltcG9ydCAqIGFzIGNvbW1vbiBmcm9tICcuL2NvbW1vbi5qcyc7XG5pbXBvcnQgKiBhcyBlcnJvcnMgZnJvbSAnLi9lcnJvcnMuanMnO1xuaW1wb3J0IHtHcmFtbWFyfSBmcm9tICcuL0dyYW1tYXIuanMnO1xuaW1wb3J0ICogYXMgcGV4cHJzIGZyb20gJy4vcGV4cHJzLmpzJztcblxuY29uc3Qgc3VwZXJTcGxpY2VQbGFjZWhvbGRlciA9IE9iamVjdC5jcmVhdGUocGV4cHJzLlBFeHByLnByb3RvdHlwZSk7XG5cbmZ1bmN0aW9uIG5hbWVzcGFjZUhhcyhucywgbmFtZSkge1xuICAvLyBMb29rIGZvciBhbiBlbnVtZXJhYmxlIHByb3BlcnR5LCBhbnl3aGVyZSBpbiB0aGUgcHJvdG90eXBlIGNoYWluLlxuICBmb3IgKGNvbnN0IHByb3AgaW4gbnMpIHtcbiAgICBpZiAocHJvcCA9PT0gbmFtZSkgcmV0dXJuIHRydWU7XG4gIH1cbiAgcmV0dXJuIGZhbHNlO1xufVxuXG4vLyBSZXR1cm5zIGEgR3JhbW1hciBpbnN0YW5jZSAoaS5lLiwgYW4gb2JqZWN0IHdpdGggYSBgbWF0Y2hgIG1ldGhvZCkgZm9yXG4vLyBgdHJlZWAsIHdoaWNoIGlzIHRoZSBjb25jcmV0ZSBzeW50YXggdHJlZSBvZiBhIHVzZXItd3JpdHRlbiBncmFtbWFyLlxuLy8gVGhlIGdyYW1tYXIgd2lsbCBiZSBhc3NpZ25lZCBpbnRvIGBuYW1lc3BhY2VgIHVuZGVyIHRoZSBuYW1lIG9mIHRoZSBncmFtbWFyXG4vLyBhcyBzcGVjaWZpZWQgaW4gdGhlIHNvdXJjZS5cbmV4cG9ydCBmdW5jdGlvbiBidWlsZEdyYW1tYXIobWF0Y2gsIG5hbWVzcGFjZSwgb3B0T2htR3JhbW1hckZvclRlc3RpbmcsIG9wdGlvbnMpIHtcbiAgY29uc3QgYnVpbGRlciA9IG5ldyBCdWlsZGVyKG9wdGlvbnMpO1xuICBsZXQgZGVjbDtcbiAgbGV0IGN1cnJlbnRSdWxlTmFtZTtcbiAgbGV0IGN1cnJlbnRSdWxlRm9ybWFscztcbiAgbGV0IG92ZXJyaWRpbmcgPSBmYWxzZTtcbiAgY29uc3QgbWV0YUdyYW1tYXIgPSBvcHRPaG1HcmFtbWFyRm9yVGVzdGluZyB8fCBvaG1HcmFtbWFyO1xuXG4gIC8vIEEgdmlzaXRvciB0aGF0IHByb2R1Y2VzIGEgR3JhbW1hciBpbnN0YW5jZSBmcm9tIHRoZSBDU1QuXG4gIGNvbnN0IGhlbHBlcnMgPSBtZXRhR3JhbW1hci5jcmVhdGVTZW1hbnRpY3MoKS5hZGRPcGVyYXRpb24oJ3Zpc2l0Jywge1xuICAgIEdyYW1tYXJzKGdyYW1tYXJJdGVyKSB7XG4gICAgICByZXR1cm4gZ3JhbW1hckl0ZXIuY2hpbGRyZW4ubWFwKGMgPT4gYy52aXNpdCgpKTtcbiAgICB9LFxuICAgIEdyYW1tYXIoaWQsIHMsIF9vcGVuLCBydWxlcywgX2Nsb3NlKSB7XG4gICAgICBjb25zdCBncmFtbWFyTmFtZSA9IGlkLnZpc2l0KCk7XG4gICAgICBkZWNsID0gYnVpbGRlci5uZXdHcmFtbWFyKGdyYW1tYXJOYW1lKTtcbiAgICAgIHMuY2hpbGQoMCkgJiYgcy5jaGlsZCgwKS52aXNpdCgpO1xuICAgICAgcnVsZXMuY2hpbGRyZW4ubWFwKGMgPT4gYy52aXNpdCgpKTtcbiAgICAgIGNvbnN0IGcgPSBkZWNsLmJ1aWxkKCk7XG4gICAgICBnLnNvdXJjZSA9IHRoaXMuc291cmNlLnRyaW1tZWQoKTtcbiAgICAgIGlmIChuYW1lc3BhY2VIYXMobmFtZXNwYWNlLCBncmFtbWFyTmFtZSkpIHtcbiAgICAgICAgdGhyb3cgZXJyb3JzLmR1cGxpY2F0ZUdyYW1tYXJEZWNsYXJhdGlvbihnLCBuYW1lc3BhY2UpO1xuICAgICAgfVxuICAgICAgbmFtZXNwYWNlW2dyYW1tYXJOYW1lXSA9IGc7XG4gICAgICByZXR1cm4gZztcbiAgICB9LFxuXG4gICAgU3VwZXJHcmFtbWFyKF8sIG4pIHtcbiAgICAgIGNvbnN0IHN1cGVyR3JhbW1hck5hbWUgPSBuLnZpc2l0KCk7XG4gICAgICBpZiAoc3VwZXJHcmFtbWFyTmFtZSA9PT0gJ251bGwnKSB7XG4gICAgICAgIGRlY2wud2l0aFN1cGVyR3JhbW1hcihudWxsKTtcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIGlmICghbmFtZXNwYWNlIHx8ICFuYW1lc3BhY2VIYXMobmFtZXNwYWNlLCBzdXBlckdyYW1tYXJOYW1lKSkge1xuICAgICAgICAgIHRocm93IGVycm9ycy51bmRlY2xhcmVkR3JhbW1hcihzdXBlckdyYW1tYXJOYW1lLCBuYW1lc3BhY2UsIG4uc291cmNlKTtcbiAgICAgICAgfVxuICAgICAgICBkZWNsLndpdGhTdXBlckdyYW1tYXIobmFtZXNwYWNlW3N1cGVyR3JhbW1hck5hbWVdKTtcbiAgICAgIH1cbiAgICB9LFxuXG4gICAgUnVsZV9kZWZpbmUobiwgZnMsIGQsIF8sIGIpIHtcbiAgICAgIGN1cnJlbnRSdWxlTmFtZSA9IG4udmlzaXQoKTtcbiAgICAgIGN1cnJlbnRSdWxlRm9ybWFscyA9IGZzLmNoaWxkcmVuLm1hcChjID0+IGMudmlzaXQoKSlbMF0gfHwgW107XG4gICAgICAvLyBJZiB0aGVyZSBpcyBubyBkZWZhdWx0IHN0YXJ0IHJ1bGUgeWV0LCBzZXQgaXQgbm93LiBUaGlzIG11c3QgYmUgZG9uZSBiZWZvcmUgdmlzaXRpbmdcbiAgICAgIC8vIHRoZSBib2R5LCBiZWNhdXNlIGl0IG1pZ2h0IGNvbnRhaW4gYW4gaW5saW5lIHJ1bGUgZGVmaW5pdGlvbi5cbiAgICAgIGlmICghZGVjbC5kZWZhdWx0U3RhcnRSdWxlICYmIGRlY2wuZW5zdXJlU3VwZXJHcmFtbWFyKCkgIT09IEdyYW1tYXIuUHJvdG9CdWlsdEluUnVsZXMpIHtcbiAgICAgICAgZGVjbC53aXRoRGVmYXVsdFN0YXJ0UnVsZShjdXJyZW50UnVsZU5hbWUpO1xuICAgICAgfVxuICAgICAgY29uc3QgYm9keSA9IGIudmlzaXQoKTtcbiAgICAgIGNvbnN0IGRlc2NyaXB0aW9uID0gZC5jaGlsZHJlbi5tYXAoYyA9PiBjLnZpc2l0KCkpWzBdO1xuICAgICAgY29uc3Qgc291cmNlID0gdGhpcy5zb3VyY2UudHJpbW1lZCgpO1xuICAgICAgcmV0dXJuIGRlY2wuZGVmaW5lKGN1cnJlbnRSdWxlTmFtZSwgY3VycmVudFJ1bGVGb3JtYWxzLCBib2R5LCBkZXNjcmlwdGlvbiwgc291cmNlKTtcbiAgICB9LFxuICAgIFJ1bGVfb3ZlcnJpZGUobiwgZnMsIF8sIGIpIHtcbiAgICAgIGN1cnJlbnRSdWxlTmFtZSA9IG4udmlzaXQoKTtcbiAgICAgIGN1cnJlbnRSdWxlRm9ybWFscyA9IGZzLmNoaWxkcmVuLm1hcChjID0+IGMudmlzaXQoKSlbMF0gfHwgW107XG5cbiAgICAgIGNvbnN0IHNvdXJjZSA9IHRoaXMuc291cmNlLnRyaW1tZWQoKTtcbiAgICAgIGRlY2wuZW5zdXJlU3VwZXJHcmFtbWFyUnVsZUZvck92ZXJyaWRpbmcoY3VycmVudFJ1bGVOYW1lLCBzb3VyY2UpO1xuXG4gICAgICBvdmVycmlkaW5nID0gdHJ1ZTtcbiAgICAgIGNvbnN0IGJvZHkgPSBiLnZpc2l0KCk7XG4gICAgICBvdmVycmlkaW5nID0gZmFsc2U7XG4gICAgICByZXR1cm4gZGVjbC5vdmVycmlkZShjdXJyZW50UnVsZU5hbWUsIGN1cnJlbnRSdWxlRm9ybWFscywgYm9keSwgbnVsbCwgc291cmNlKTtcbiAgICB9LFxuICAgIFJ1bGVfZXh0ZW5kKG4sIGZzLCBfLCBiKSB7XG4gICAgICBjdXJyZW50UnVsZU5hbWUgPSBuLnZpc2l0KCk7XG4gICAgICBjdXJyZW50UnVsZUZvcm1hbHMgPSBmcy5jaGlsZHJlbi5tYXAoYyA9PiBjLnZpc2l0KCkpWzBdIHx8IFtdO1xuICAgICAgY29uc3QgYm9keSA9IGIudmlzaXQoKTtcbiAgICAgIGNvbnN0IHNvdXJjZSA9IHRoaXMuc291cmNlLnRyaW1tZWQoKTtcbiAgICAgIHJldHVybiBkZWNsLmV4dGVuZChjdXJyZW50UnVsZU5hbWUsIGN1cnJlbnRSdWxlRm9ybWFscywgYm9keSwgbnVsbCwgc291cmNlKTtcbiAgICB9LFxuICAgIFJ1bGVCb2R5KF8sIHRlcm1zKSB7XG4gICAgICByZXR1cm4gYnVpbGRlci5hbHQoLi4udGVybXMudmlzaXQoKSkud2l0aFNvdXJjZSh0aGlzLnNvdXJjZSk7XG4gICAgfSxcbiAgICBPdmVycmlkZVJ1bGVCb2R5KF8sIHRlcm1zKSB7XG4gICAgICBjb25zdCBhcmdzID0gdGVybXMudmlzaXQoKTtcblxuICAgICAgLy8gQ2hlY2sgaWYgdGhlIHN1cGVyLXNwbGljZSBvcGVyYXRvciAoYC4uLmApIGFwcGVhcnMgaW4gdGhlIHRlcm1zLlxuICAgICAgY29uc3QgZXhwYW5zaW9uUG9zID0gYXJncy5pbmRleE9mKHN1cGVyU3BsaWNlUGxhY2Vob2xkZXIpO1xuICAgICAgaWYgKGV4cGFuc2lvblBvcyA+PSAwKSB7XG4gICAgICAgIGNvbnN0IGJlZm9yZVRlcm1zID0gYXJncy5zbGljZSgwLCBleHBhbnNpb25Qb3MpO1xuICAgICAgICBjb25zdCBhZnRlclRlcm1zID0gYXJncy5zbGljZShleHBhbnNpb25Qb3MgKyAxKTtcblxuICAgICAgICAvLyBFbnN1cmUgaXQgYXBwZWFycyBubyBtb3JlIHRoYW4gb25jZS5cbiAgICAgICAgYWZ0ZXJUZXJtcy5mb3JFYWNoKHQgPT4ge1xuICAgICAgICAgIGlmICh0ID09PSBzdXBlclNwbGljZVBsYWNlaG9sZGVyKSB0aHJvdyBlcnJvcnMubXVsdGlwbGVTdXBlclNwbGljZXModCk7XG4gICAgICAgIH0pO1xuXG4gICAgICAgIHJldHVybiBuZXcgcGV4cHJzLlNwbGljZShcbiAgICAgICAgICBkZWNsLnN1cGVyR3JhbW1hcixcbiAgICAgICAgICBjdXJyZW50UnVsZU5hbWUsXG4gICAgICAgICAgYmVmb3JlVGVybXMsXG4gICAgICAgICAgYWZ0ZXJUZXJtc1xuICAgICAgICApLndpdGhTb3VyY2UodGhpcy5zb3VyY2UpO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcmV0dXJuIGJ1aWxkZXIuYWx0KC4uLmFyZ3MpLndpdGhTb3VyY2UodGhpcy5zb3VyY2UpO1xuICAgICAgfVxuICAgIH0sXG4gICAgRm9ybWFscyhvcG9pbnR5LCBmcywgY3BvaW50eSkge1xuICAgICAgcmV0dXJuIGZzLnZpc2l0KCk7XG4gICAgfSxcblxuICAgIFBhcmFtcyhvcG9pbnR5LCBwcywgY3BvaW50eSkge1xuICAgICAgcmV0dXJuIHBzLnZpc2l0KCk7XG4gICAgfSxcblxuICAgIEFsdChzZXFzKSB7XG4gICAgICByZXR1cm4gYnVpbGRlci5hbHQoLi4uc2Vxcy52aXNpdCgpKS53aXRoU291cmNlKHRoaXMuc291cmNlKTtcbiAgICB9LFxuXG4gICAgVG9wTGV2ZWxUZXJtX2lubGluZShiLCBuKSB7XG4gICAgICBjb25zdCBpbmxpbmVSdWxlTmFtZSA9IGN1cnJlbnRSdWxlTmFtZSArICdfJyArIG4udmlzaXQoKTtcbiAgICAgIGNvbnN0IGJvZHkgPSBiLnZpc2l0KCk7XG4gICAgICBjb25zdCBzb3VyY2UgPSB0aGlzLnNvdXJjZS50cmltbWVkKCk7XG4gICAgICBjb25zdCBpc05ld1J1bGVEZWNsYXJhdGlvbiA9ICEoXG4gICAgICAgIGRlY2wuc3VwZXJHcmFtbWFyICYmIGRlY2wuc3VwZXJHcmFtbWFyLnJ1bGVzW2lubGluZVJ1bGVOYW1lXVxuICAgICAgKTtcbiAgICAgIGlmIChvdmVycmlkaW5nICYmICFpc05ld1J1bGVEZWNsYXJhdGlvbikge1xuICAgICAgICBkZWNsLm92ZXJyaWRlKGlubGluZVJ1bGVOYW1lLCBjdXJyZW50UnVsZUZvcm1hbHMsIGJvZHksIG51bGwsIHNvdXJjZSk7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBkZWNsLmRlZmluZShpbmxpbmVSdWxlTmFtZSwgY3VycmVudFJ1bGVGb3JtYWxzLCBib2R5LCBudWxsLCBzb3VyY2UpO1xuICAgICAgfVxuICAgICAgY29uc3QgcGFyYW1zID0gY3VycmVudFJ1bGVGb3JtYWxzLm1hcChmb3JtYWwgPT4gYnVpbGRlci5hcHAoZm9ybWFsKSk7XG4gICAgICByZXR1cm4gYnVpbGRlci5hcHAoaW5saW5lUnVsZU5hbWUsIHBhcmFtcykud2l0aFNvdXJjZShib2R5LnNvdXJjZSk7XG4gICAgfSxcbiAgICBPdmVycmlkZVRvcExldmVsVGVybV9zdXBlclNwbGljZShfKSB7XG4gICAgICByZXR1cm4gc3VwZXJTcGxpY2VQbGFjZWhvbGRlcjtcbiAgICB9LFxuXG4gICAgU2VxKGV4cHIpIHtcbiAgICAgIHJldHVybiBidWlsZGVyLnNlcSguLi5leHByLmNoaWxkcmVuLm1hcChjID0+IGMudmlzaXQoKSkpLndpdGhTb3VyY2UodGhpcy5zb3VyY2UpO1xuICAgIH0sXG5cbiAgICBJdGVyX3N0YXIoeCwgXykge1xuICAgICAgcmV0dXJuIGJ1aWxkZXIuc3Rhcih4LnZpc2l0KCkpLndpdGhTb3VyY2UodGhpcy5zb3VyY2UpO1xuICAgIH0sXG4gICAgSXRlcl9wbHVzKHgsIF8pIHtcbiAgICAgIHJldHVybiBidWlsZGVyLnBsdXMoeC52aXNpdCgpKS53aXRoU291cmNlKHRoaXMuc291cmNlKTtcbiAgICB9LFxuICAgIEl0ZXJfb3B0KHgsIF8pIHtcbiAgICAgIHJldHVybiBidWlsZGVyLm9wdCh4LnZpc2l0KCkpLndpdGhTb3VyY2UodGhpcy5zb3VyY2UpO1xuICAgIH0sXG5cbiAgICBQcmVkX25vdChfLCB4KSB7XG4gICAgICByZXR1cm4gYnVpbGRlci5ub3QoeC52aXNpdCgpKS53aXRoU291cmNlKHRoaXMuc291cmNlKTtcbiAgICB9LFxuICAgIFByZWRfbG9va2FoZWFkKF8sIHgpIHtcbiAgICAgIHJldHVybiBidWlsZGVyLmxvb2thaGVhZCh4LnZpc2l0KCkpLndpdGhTb3VyY2UodGhpcy5zb3VyY2UpO1xuICAgIH0sXG5cbiAgICBMZXhfbGV4KF8sIHgpIHtcbiAgICAgIHJldHVybiBidWlsZGVyLmxleCh4LnZpc2l0KCkpLndpdGhTb3VyY2UodGhpcy5zb3VyY2UpO1xuICAgIH0sXG5cbiAgICBCYXNlX2FwcGxpY2F0aW9uKHJ1bGUsIHBzKSB7XG4gICAgICBjb25zdCBwYXJhbXMgPSBwcy5jaGlsZHJlbi5tYXAoYyA9PiBjLnZpc2l0KCkpWzBdIHx8IFtdO1xuICAgICAgcmV0dXJuIGJ1aWxkZXIuYXBwKHJ1bGUudmlzaXQoKSwgcGFyYW1zKS53aXRoU291cmNlKHRoaXMuc291cmNlKTtcbiAgICB9LFxuICAgIEJhc2VfcmFuZ2UoZnJvbSwgXywgdG8pIHtcbiAgICAgIHJldHVybiBidWlsZGVyLnJhbmdlKGZyb20udmlzaXQoKSwgdG8udmlzaXQoKSkud2l0aFNvdXJjZSh0aGlzLnNvdXJjZSk7XG4gICAgfSxcbiAgICBCYXNlX3Rlcm1pbmFsKGV4cHIpIHtcbiAgICAgIHJldHVybiBidWlsZGVyLnRlcm1pbmFsKGV4cHIudmlzaXQoKSkud2l0aFNvdXJjZSh0aGlzLnNvdXJjZSk7XG4gICAgfSxcbiAgICBCYXNlX3BhcmVuKG9wZW4sIHgsIGNsb3NlKSB7XG4gICAgICByZXR1cm4geC52aXNpdCgpO1xuICAgIH0sXG5cbiAgICBydWxlRGVzY3Iob3BlbiwgdCwgY2xvc2UpIHtcbiAgICAgIHJldHVybiB0LnZpc2l0KCk7XG4gICAgfSxcbiAgICBydWxlRGVzY3JUZXh0KF8pIHtcbiAgICAgIHJldHVybiB0aGlzLnNvdXJjZVN0cmluZy50cmltKCk7XG4gICAgfSxcblxuICAgIGNhc2VOYW1lKF8sIHNwYWNlMSwgbiwgc3BhY2UyLCBlbmQpIHtcbiAgICAgIHJldHVybiBuLnZpc2l0KCk7XG4gICAgfSxcblxuICAgIG5hbWUoZmlyc3QsIHJlc3QpIHtcbiAgICAgIHJldHVybiB0aGlzLnNvdXJjZVN0cmluZztcbiAgICB9LFxuICAgIG5hbWVGaXJzdChleHByKSB7fSxcbiAgICBuYW1lUmVzdChleHByKSB7fSxcblxuICAgIHRlcm1pbmFsKG9wZW4sIGNzLCBjbG9zZSkge1xuICAgICAgcmV0dXJuIGNzLmNoaWxkcmVuLm1hcChjID0+IGMudmlzaXQoKSkuam9pbignJyk7XG4gICAgfSxcblxuICAgIG9uZUNoYXJUZXJtaW5hbChvcGVuLCBjLCBjbG9zZSkge1xuICAgICAgcmV0dXJuIGMudmlzaXQoKTtcbiAgICB9LFxuXG4gICAgZXNjYXBlQ2hhcihjKSB7XG4gICAgICB0cnkge1xuICAgICAgICByZXR1cm4gY29tbW9uLnVuZXNjYXBlQ29kZVBvaW50KHRoaXMuc291cmNlU3RyaW5nKTtcbiAgICAgIH0gY2F0Y2ggKGVycikge1xuICAgICAgICBpZiAoZXJyIGluc3RhbmNlb2YgUmFuZ2VFcnJvciAmJiBlcnIubWVzc2FnZS5zdGFydHNXaXRoKCdJbnZhbGlkIGNvZGUgcG9pbnQgJykpIHtcbiAgICAgICAgICB0aHJvdyBlcnJvcnMuaW52YWxpZENvZGVQb2ludChjKTtcbiAgICAgICAgfVxuICAgICAgICB0aHJvdyBlcnI7IC8vIFJldGhyb3dcbiAgICAgIH1cbiAgICB9LFxuXG4gICAgTm9uZW1wdHlMaXN0T2YoeCwgXywgeHMpIHtcbiAgICAgIHJldHVybiBbeC52aXNpdCgpXS5jb25jYXQoeHMuY2hpbGRyZW4ubWFwKGMgPT4gYy52aXNpdCgpKSk7XG4gICAgfSxcbiAgICBFbXB0eUxpc3RPZigpIHtcbiAgICAgIHJldHVybiBbXTtcbiAgICB9LFxuXG4gICAgX3Rlcm1pbmFsKCkge1xuICAgICAgcmV0dXJuIHRoaXMuc291cmNlU3RyaW5nO1xuICAgIH0sXG4gIH0pO1xuICByZXR1cm4gaGVscGVycyhtYXRjaCkudmlzaXQoKTtcbn1cbiIsImltcG9ydCB7bWFrZVJlY2lwZX0gZnJvbSAnLi4vc3JjL21haW4ta2VybmVsLmpzJztcbmV4cG9ydCBkZWZhdWx0IG1ha2VSZWNpcGUoW1wiZ3JhbW1hclwiLHtcInNvdXJjZVwiOlwiT3BlcmF0aW9uc0FuZEF0dHJpYnV0ZXMge1xcblxcbiAgQXR0cmlidXRlU2lnbmF0dXJlID1cXG4gICAgbmFtZVxcblxcbiAgT3BlcmF0aW9uU2lnbmF0dXJlID1cXG4gICAgbmFtZSBGb3JtYWxzP1xcblxcbiAgRm9ybWFsc1xcbiAgICA9IFxcXCIoXFxcIiBMaXN0T2Y8bmFtZSwgXFxcIixcXFwiPiBcXFwiKVxcXCJcXG5cXG4gIG5hbWUgIChhIG5hbWUpXFxuICAgID0gbmFtZUZpcnN0IG5hbWVSZXN0KlxcblxcbiAgbmFtZUZpcnN0XFxuICAgID0gXFxcIl9cXFwiXFxuICAgIHwgbGV0dGVyXFxuXFxuICBuYW1lUmVzdFxcbiAgICA9IFxcXCJfXFxcIlxcbiAgICB8IGFsbnVtXFxuXFxufVwifSxcIk9wZXJhdGlvbnNBbmRBdHRyaWJ1dGVzXCIsbnVsbCxcIkF0dHJpYnV0ZVNpZ25hdHVyZVwiLHtcIkF0dHJpYnV0ZVNpZ25hdHVyZVwiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzI5LDU4XX0sbnVsbCxbXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls1NCw1OF19LFwibmFtZVwiLFtdXV0sXCJPcGVyYXRpb25TaWduYXR1cmVcIjpbXCJkZWZpbmVcIix7XCJzb3VyY2VJbnRlcnZhbFwiOls2MiwxMDBdfSxudWxsLFtdLFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6Wzg3LDEwMF19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6Wzg3LDkxXX0sXCJuYW1lXCIsW11dLFtcIm9wdFwiLHtcInNvdXJjZUludGVydmFsXCI6WzkyLDEwMF19LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzkyLDk5XX0sXCJGb3JtYWxzXCIsW11dXV1dLFwiRm9ybWFsc1wiOltcImRlZmluZVwiLHtcInNvdXJjZUludGVydmFsXCI6WzEwNCwxNDNdfSxudWxsLFtdLFtcInNlcVwiLHtcInNvdXJjZUludGVydmFsXCI6WzExOCwxNDNdfSxbXCJ0ZXJtaW5hbFwiLHtcInNvdXJjZUludGVydmFsXCI6WzExOCwxMjFdfSxcIihcIl0sW1wiYXBwXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTIyLDEzOV19LFwiTGlzdE9mXCIsW1tcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzEyOSwxMzNdfSxcIm5hbWVcIixbXV0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxMzUsMTM4XX0sXCIsXCJdXV0sW1widGVybWluYWxcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsxNDAsMTQzXX0sXCIpXCJdXV0sXCJuYW1lXCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTQ3LDE4N119LFwiYSBuYW1lXCIsW10sW1wic2VxXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTY4LDE4N119LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE2OCwxNzddfSxcIm5hbWVGaXJzdFwiLFtdXSxbXCJzdGFyXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTc4LDE4N119LFtcImFwcFwiLHtcInNvdXJjZUludGVydmFsXCI6WzE3OCwxODZdfSxcIm5hbWVSZXN0XCIsW11dXV1dLFwibmFtZUZpcnN0XCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMTkxLDIyM119LG51bGwsW10sW1wiYWx0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjA3LDIyM119LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjA3LDIxMF19LFwiX1wiXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyMTcsMjIzXX0sXCJsZXR0ZXJcIixbXV1dXSxcIm5hbWVSZXN0XCI6W1wiZGVmaW5lXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjI3LDI1N119LG51bGwsW10sW1wiYWx0XCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjQyLDI1N119LFtcInRlcm1pbmFsXCIse1wic291cmNlSW50ZXJ2YWxcIjpbMjQyLDI0NV19LFwiX1wiXSxbXCJhcHBcIix7XCJzb3VyY2VJbnRlcnZhbFwiOlsyNTIsMjU3XX0sXCJhbG51bVwiLFtdXV1dfV0pO1xuIiwiaW1wb3J0IG9wZXJhdGlvbnNBbmRBdHRyaWJ1dGVzR3JhbW1hciBmcm9tICcuLi9kaXN0L29wZXJhdGlvbnMtYW5kLWF0dHJpYnV0ZXMuanMnO1xuaW1wb3J0IHtHcmFtbWFyfSBmcm9tICcuL0dyYW1tYXIuanMnO1xuaW1wb3J0IHtTZW1hbnRpY3N9IGZyb20gJy4vU2VtYW50aWNzLmpzJztcblxuaW5pdEJ1aWx0SW5TZW1hbnRpY3MoR3JhbW1hci5CdWlsdEluUnVsZXMpO1xuaW5pdFByb3RvdHlwZVBhcnNlcihvcGVyYXRpb25zQW5kQXR0cmlidXRlc0dyYW1tYXIpOyAvLyByZXF1aXJlcyBCdWlsdEluU2VtYW50aWNzXG5cbmZ1bmN0aW9uIGluaXRCdWlsdEluU2VtYW50aWNzKGJ1aWx0SW5SdWxlcykge1xuICBjb25zdCBhY3Rpb25zID0ge1xuICAgIGVtcHR5KCkge1xuICAgICAgcmV0dXJuIHRoaXMuaXRlcmF0aW9uKCk7XG4gICAgfSxcbiAgICBub25FbXB0eShmaXJzdCwgXywgcmVzdCkge1xuICAgICAgcmV0dXJuIHRoaXMuaXRlcmF0aW9uKFtmaXJzdF0uY29uY2F0KHJlc3QuY2hpbGRyZW4pKTtcbiAgICB9LFxuICAgIHNlbGYoLi4uX2NoaWxkcmVuKSB7XG4gICAgICByZXR1cm4gdGhpcztcbiAgICB9LFxuICB9O1xuXG4gIFNlbWFudGljcy5CdWlsdEluU2VtYW50aWNzID0gU2VtYW50aWNzLmNyZWF0ZVNlbWFudGljcyhidWlsdEluUnVsZXMsIG51bGwpLmFkZE9wZXJhdGlvbihcbiAgICAnYXNJdGVyYXRpb24nLFxuICAgIHtcbiAgICAgIGVtcHR5TGlzdE9mOiBhY3Rpb25zLmVtcHR5LFxuICAgICAgbm9uZW1wdHlMaXN0T2Y6IGFjdGlvbnMubm9uRW1wdHksXG4gICAgICBFbXB0eUxpc3RPZjogYWN0aW9ucy5lbXB0eSxcbiAgICAgIE5vbmVtcHR5TGlzdE9mOiBhY3Rpb25zLm5vbkVtcHR5LFxuICAgICAgX2l0ZXI6IGFjdGlvbnMuc2VsZixcbiAgICB9XG4gICk7XG59XG5cbmZ1bmN0aW9uIGluaXRQcm90b3R5cGVQYXJzZXIoZ3JhbW1hcikge1xuICBTZW1hbnRpY3MucHJvdG90eXBlR3JhbW1hclNlbWFudGljcyA9IGdyYW1tYXIuY3JlYXRlU2VtYW50aWNzKCkuYWRkT3BlcmF0aW9uKCdwYXJzZScsIHtcbiAgICBBdHRyaWJ1dGVTaWduYXR1cmUobmFtZSkge1xuICAgICAgcmV0dXJuIHtcbiAgICAgICAgbmFtZTogbmFtZS5wYXJzZSgpLFxuICAgICAgICBmb3JtYWxzOiBbXSxcbiAgICAgIH07XG4gICAgfSxcbiAgICBPcGVyYXRpb25TaWduYXR1cmUobmFtZSwgb3B0Rm9ybWFscykge1xuICAgICAgcmV0dXJuIHtcbiAgICAgICAgbmFtZTogbmFtZS5wYXJzZSgpLFxuICAgICAgICBmb3JtYWxzOiBvcHRGb3JtYWxzLmNoaWxkcmVuLm1hcChjID0+IGMucGFyc2UoKSlbMF0gfHwgW10sXG4gICAgICB9O1xuICAgIH0sXG4gICAgRm9ybWFscyhvcGFyZW4sIGZzLCBjcGFyZW4pIHtcbiAgICAgIHJldHVybiBmcy5hc0l0ZXJhdGlvbigpLmNoaWxkcmVuLm1hcChjID0+IGMucGFyc2UoKSk7XG4gICAgfSxcbiAgICBuYW1lKGZpcnN0LCByZXN0KSB7XG4gICAgICByZXR1cm4gdGhpcy5zb3VyY2VTdHJpbmc7XG4gICAgfSxcbiAgfSk7XG4gIFNlbWFudGljcy5wcm90b3R5cGVHcmFtbWFyID0gZ3JhbW1hcjtcbn1cbiIsImV4cG9ydCBmdW5jdGlvbiBmaW5kSW5kZW50YXRpb24oaW5wdXQpIHtcbiAgbGV0IHBvcyA9IDA7XG4gIGNvbnN0IHN0YWNrID0gWzBdO1xuICBjb25zdCB0b3BPZlN0YWNrID0gKCkgPT4gc3RhY2tbc3RhY2subGVuZ3RoIC0gMV07XG5cbiAgY29uc3QgcmVzdWx0ID0ge307XG5cbiAgY29uc3QgcmVnZXggPSAvKCAqKS4qKD86JHxcXHI/XFxufFxccikvZztcbiAgbGV0IG1hdGNoO1xuICB3aGlsZSAoKG1hdGNoID0gcmVnZXguZXhlYyhpbnB1dCkpICE9IG51bGwpIHtcbiAgICBjb25zdCBbbGluZSwgaW5kZW50XSA9IG1hdGNoO1xuXG4gICAgLy8gVGhlIGxhc3QgbWF0Y2ggd2lsbCBhbHdheXMgaGF2ZSBsZW5ndGggMC4gSW4gZXZlcnkgb3RoZXIgY2FzZSwgc29tZVxuICAgIC8vIGNoYXJhY3RlcnMgd2lsbCBiZSBtYXRjaGVkIChwb3NzaWJseSBvbmx5IHRoZSBlbmQgb2YgbGluZSBjaGFycykuXG4gICAgaWYgKGxpbmUubGVuZ3RoID09PSAwKSBicmVhaztcblxuICAgIGNvbnN0IGluZGVudFNpemUgPSBpbmRlbnQubGVuZ3RoO1xuICAgIGNvbnN0IHByZXZTaXplID0gdG9wT2ZTdGFjaygpO1xuXG4gICAgY29uc3QgaW5kZW50UG9zID0gcG9zICsgaW5kZW50U2l6ZTtcblxuICAgIGlmIChpbmRlbnRTaXplID4gcHJldlNpemUpIHtcbiAgICAgIC8vIEluZGVudCAtLSBhbHdheXMgb25seSAxLlxuICAgICAgc3RhY2sucHVzaChpbmRlbnRTaXplKTtcbiAgICAgIHJlc3VsdFtpbmRlbnRQb3NdID0gMTtcbiAgICB9IGVsc2UgaWYgKGluZGVudFNpemUgPCBwcmV2U2l6ZSkge1xuICAgICAgLy8gRGVkZW50IC0tIGNhbiBiZSBtdWx0aXBsZSBsZXZlbHMuXG4gICAgICBjb25zdCBwcmV2TGVuZ3RoID0gc3RhY2subGVuZ3RoO1xuICAgICAgd2hpbGUgKHRvcE9mU3RhY2soKSAhPT0gaW5kZW50U2l6ZSkge1xuICAgICAgICBzdGFjay5wb3AoKTtcbiAgICAgIH1cbiAgICAgIHJlc3VsdFtpbmRlbnRQb3NdID0gLTEgKiAocHJldkxlbmd0aCAtIHN0YWNrLmxlbmd0aCk7XG4gICAgfVxuICAgIHBvcyArPSBsaW5lLmxlbmd0aDtcbiAgfVxuICAvLyBFbnN1cmUgdGhhdCB0aGVyZSBpcyBhIG1hdGNoaW5nIERFREVOVCBmb3IgZXZlcnkgcmVtYWluaW5nIElOREVOVC5cbiAgaWYgKHN0YWNrLmxlbmd0aCA+IDEpIHtcbiAgICByZXN1bHRbcG9zXSA9IDEgLSBzdGFjay5sZW5ndGg7XG4gIH1cbiAgcmV0dXJuIHJlc3VsdDtcbn1cbiIsImltcG9ydCBCdWlsdEluUnVsZXMgZnJvbSAnLi4vZGlzdC9idWlsdC1pbi1ydWxlcy5qcyc7XG5pbXBvcnQge0J1aWxkZXJ9IGZyb20gJy4uL3NyYy9CdWlsZGVyLmpzJztcbmltcG9ydCB7RmFpbHVyZX0gZnJvbSAnLi4vc3JjL0ZhaWx1cmUuanMnO1xuaW1wb3J0IHtUZXJtaW5hbE5vZGV9IGZyb20gJy4uL3NyYy9ub2Rlcy5qcyc7XG5pbXBvcnQgKiBhcyBwZXhwcnMgZnJvbSAnLi4vc3JjL3BleHBycy5qcyc7XG5pbXBvcnQge2ZpbmRJbmRlbnRhdGlvbn0gZnJvbSAnLi9maW5kSW5kZW50YXRpb24uanMnO1xuaW1wb3J0IHtJbnB1dFN0cmVhbX0gZnJvbSAnLi9JbnB1dFN0cmVhbS5qcyc7XG5cbmNvbnN0IElOREVOVF9ERVNDUklQVElPTiA9ICdhbiBpbmRlbnRlZCBibG9jayc7XG5jb25zdCBERURFTlRfREVTQ1JJUFRJT04gPSAnYSBkZWRlbnQnO1xuXG4vLyBBIHNlbnRpbmVsIHZhbHVlIHRoYXQgaXMgb3V0IG9mIHJhbmdlIGZvciBib3RoIGNoYXJDb2RlQXQoKSBhbmQgY29kZVBvaW50QXQoKS5cbmNvbnN0IElOVkFMSURfQ09ERV9QT0lOVCA9IDB4MTBmZmZmICsgMTtcblxuY2xhc3MgSW5wdXRTdHJlYW1XaXRoSW5kZW50YXRpb24gZXh0ZW5kcyBJbnB1dFN0cmVhbSB7XG4gIGNvbnN0cnVjdG9yKHN0YXRlKSB7XG4gICAgc3VwZXIoc3RhdGUuaW5wdXQpO1xuICAgIHRoaXMuc3RhdGUgPSBzdGF0ZTtcbiAgfVxuXG4gIF9pbmRlbnRhdGlvbkF0KHBvcykge1xuICAgIHJldHVybiB0aGlzLnN0YXRlLnVzZXJEYXRhW3Bvc10gfHwgMDtcbiAgfVxuXG4gIGF0RW5kKCkge1xuICAgIHJldHVybiBzdXBlci5hdEVuZCgpICYmIHRoaXMuX2luZGVudGF0aW9uQXQodGhpcy5wb3MpID09PSAwO1xuICB9XG5cbiAgbmV4dCgpIHtcbiAgICBpZiAodGhpcy5faW5kZW50YXRpb25BdCh0aGlzLnBvcykgIT09IDApIHtcbiAgICAgIHRoaXMuZXhhbWluZWRMZW5ndGggPSBNYXRoLm1heCh0aGlzLmV4YW1pbmVkTGVuZ3RoLCB0aGlzLnBvcyk7XG4gICAgICByZXR1cm4gdW5kZWZpbmVkO1xuICAgIH1cbiAgICByZXR1cm4gc3VwZXIubmV4dCgpO1xuICB9XG5cbiAgbmV4dENoYXJDb2RlKCkge1xuICAgIGlmICh0aGlzLl9pbmRlbnRhdGlvbkF0KHRoaXMucG9zKSAhPT0gMCkge1xuICAgICAgdGhpcy5leGFtaW5lZExlbmd0aCA9IE1hdGgubWF4KHRoaXMuZXhhbWluZWRMZW5ndGgsIHRoaXMucG9zKTtcbiAgICAgIHJldHVybiBJTlZBTElEX0NPREVfUE9JTlQ7XG4gICAgfVxuICAgIHJldHVybiBzdXBlci5uZXh0Q2hhckNvZGUoKTtcbiAgfVxuXG4gIG5leHRDb2RlUG9pbnQoKSB7XG4gICAgaWYgKHRoaXMuX2luZGVudGF0aW9uQXQodGhpcy5wb3MpICE9PSAwKSB7XG4gICAgICB0aGlzLmV4YW1pbmVkTGVuZ3RoID0gTWF0aC5tYXgodGhpcy5leGFtaW5lZExlbmd0aCwgdGhpcy5wb3MpO1xuICAgICAgcmV0dXJuIElOVkFMSURfQ09ERV9QT0lOVDtcbiAgICB9XG4gICAgcmV0dXJuIHN1cGVyLm5leHRDb2RlUG9pbnQoKTtcbiAgfVxufVxuXG5jbGFzcyBJbmRlbnRhdGlvbiBleHRlbmRzIHBleHBycy5QRXhwciB7XG4gIGNvbnN0cnVjdG9yKGlzSW5kZW50ID0gdHJ1ZSkge1xuICAgIHN1cGVyKCk7XG4gICAgdGhpcy5pc0luZGVudCA9IGlzSW5kZW50O1xuICB9XG5cbiAgYWxsb3dzU2tpcHBpbmdQcmVjZWRpbmdTcGFjZSgpIHtcbiAgICByZXR1cm4gdHJ1ZTtcbiAgfVxuXG4gIGV2YWwoc3RhdGUpIHtcbiAgICBjb25zdCB7aW5wdXRTdHJlYW19ID0gc3RhdGU7XG4gICAgY29uc3QgcHNldWRvVG9rZW5zID0gc3RhdGUudXNlckRhdGE7XG4gICAgc3RhdGUuZG9Ob3RNZW1vaXplID0gdHJ1ZTtcblxuICAgIGNvbnN0IG9yaWdQb3MgPSBpbnB1dFN0cmVhbS5wb3M7XG5cbiAgICBjb25zdCBzaWduID0gdGhpcy5pc0luZGVudCA/IDEgOiAtMTtcbiAgICBjb25zdCBjb3VudCA9IChwc2V1ZG9Ub2tlbnNbb3JpZ1Bvc10gfHwgMCkgKiBzaWduO1xuICAgIGlmIChjb3VudCA+IDApIHtcbiAgICAgIC8vIFVwZGF0ZSB0aGUgY291bnQgdG8gY29uc3VtZSB0aGUgcHNldWRvdG9rZW4uXG4gICAgICBzdGF0ZS51c2VyRGF0YSA9IE9iamVjdC5jcmVhdGUocHNldWRvVG9rZW5zKTtcbiAgICAgIHN0YXRlLnVzZXJEYXRhW29yaWdQb3NdIC09IHNpZ247XG5cbiAgICAgIHN0YXRlLnB1c2hCaW5kaW5nKG5ldyBUZXJtaW5hbE5vZGUoMCksIG9yaWdQb3MpO1xuICAgICAgcmV0dXJuIHRydWU7XG4gICAgfSBlbHNlIHtcbiAgICAgIHN0YXRlLnByb2Nlc3NGYWlsdXJlKG9yaWdQb3MsIHRoaXMpO1xuICAgICAgcmV0dXJuIGZhbHNlO1xuICAgIH1cbiAgfVxuXG4gIGdldEFyaXR5KCkge1xuICAgIHJldHVybiAxO1xuICB9XG5cbiAgX2Fzc2VydEFsbEFwcGxpY2F0aW9uc0FyZVZhbGlkKHJ1bGVOYW1lLCBncmFtbWFyKSB7fVxuXG4gIF9pc051bGxhYmxlKGdyYW1tYXIsIG1lbW8pIHtcbiAgICByZXR1cm4gZmFsc2U7XG4gIH1cblxuICBhc3NlcnRDaG9pY2VzSGF2ZVVuaWZvcm1Bcml0eShydWxlTmFtZSkge31cblxuICBhc3NlcnRJdGVyYXRlZEV4cHJzQXJlTm90TnVsbGFibGUoZ3JhbW1hcikge31cblxuICBpbnRyb2R1Y2VQYXJhbXMoZm9ybWFscykge1xuICAgIHJldHVybiB0aGlzO1xuICB9XG5cbiAgc3Vic3RpdHV0ZVBhcmFtcyhhY3R1YWxzKSB7XG4gICAgcmV0dXJuIHRoaXM7XG4gIH1cblxuICB0b1N0cmluZygpIHtcbiAgICByZXR1cm4gdGhpcy5pc0luZGVudCA/ICdpbmRlbnQnIDogJ2RlZGVudCc7XG4gIH1cblxuICB0b0Rpc3BsYXlTdHJpbmcoKSB7XG4gICAgcmV0dXJuIHRoaXMudG9TdHJpbmcoKTtcbiAgfVxuXG4gIHRvRmFpbHVyZShncmFtbWFyKSB7XG4gICAgY29uc3QgZGVzY3JpcHRpb24gPSB0aGlzLmlzSW5kZW50ID8gSU5ERU5UX0RFU0NSSVBUSU9OIDogREVERU5UX0RFU0NSSVBUSU9OO1xuICAgIHJldHVybiBuZXcgRmFpbHVyZSh0aGlzLCBkZXNjcmlwdGlvbiwgJ2Rlc2NyaXB0aW9uJyk7XG4gIH1cbn1cblxuLy8gQ3JlYXRlIGEgbmV3IGRlZmluaXRpb24gZm9yIGBhbnlgIHRoYXQgY2FuIGNvbnN1bWUgaW5kZW50ICYgZGVkZW50LlxuY29uc3QgYXBwbHlJbmRlbnQgPSBuZXcgcGV4cHJzLkFwcGx5KCdpbmRlbnQnKTtcbmNvbnN0IGFwcGx5RGVkZW50ID0gbmV3IHBleHBycy5BcHBseSgnZGVkZW50Jyk7XG5jb25zdCBuZXdBbnlCb2R5ID0gbmV3IHBleHBycy5TcGxpY2UoQnVpbHRJblJ1bGVzLCAnYW55JywgW2FwcGx5SW5kZW50LCBhcHBseURlZGVudF0sIFtdKTtcblxuZXhwb3J0IGNvbnN0IEluZGVudGF0aW9uU2Vuc2l0aXZlID0gbmV3IEJ1aWxkZXIoKVxuICAubmV3R3JhbW1hcignSW5kZW50YXRpb25TZW5zaXRpdmUnKVxuICAud2l0aFN1cGVyR3JhbW1hcihCdWlsdEluUnVsZXMpXG4gIC5kZWZpbmUoJ2luZGVudCcsIFtdLCBuZXcgSW5kZW50YXRpb24odHJ1ZSksIElOREVOVF9ERVNDUklQVElPTiwgdW5kZWZpbmVkLCB0cnVlKVxuICAuZGVmaW5lKCdkZWRlbnQnLCBbXSwgbmV3IEluZGVudGF0aW9uKGZhbHNlKSwgREVERU5UX0RFU0NSSVBUSU9OLCB1bmRlZmluZWQsIHRydWUpXG4gIC5leHRlbmQoJ2FueScsIFtdLCBuZXdBbnlCb2R5LCAnYW55IGNoYXJhY3RlcicsIHVuZGVmaW5lZClcbiAgLmJ1aWxkKCk7XG5cbk9iamVjdC5hc3NpZ24oSW5kZW50YXRpb25TZW5zaXRpdmUsIHtcbiAgX21hdGNoU3RhdGVJbml0aWFsaXplcihzdGF0ZSkge1xuICAgIHN0YXRlLnVzZXJEYXRhID0gZmluZEluZGVudGF0aW9uKHN0YXRlLmlucHV0KTtcbiAgICBzdGF0ZS5pbnB1dFN0cmVhbSA9IG5ldyBJbnB1dFN0cmVhbVdpdGhJbmRlbnRhdGlvbihzdGF0ZSk7XG4gIH0sXG4gIHN1cHBvcnRzSW5jcmVtZW50YWxQYXJzaW5nOiBmYWxzZSxcbn0pO1xuIiwiLy8gR2VuZXJhdGVkIGJ5IHNjcmlwdHMvcHJlYnVpbGQuanNcbmV4cG9ydCBjb25zdCB2ZXJzaW9uID0gJzE3LjUuMCc7XG4iLCJpbXBvcnQgb2htR3JhbW1hciBmcm9tICcuLi9kaXN0L29obS1ncmFtbWFyLmpzJztcbmltcG9ydCB7YnVpbGRHcmFtbWFyfSBmcm9tICcuL2J1aWxkR3JhbW1hci5qcyc7XG5pbXBvcnQgKiBhcyBjb21tb24gZnJvbSAnLi9jb21tb24uanMnO1xuaW1wb3J0ICogYXMgZXJyb3JzIGZyb20gJy4vZXJyb3JzLmpzJztcbmltcG9ydCB7R3JhbW1hcn0gZnJvbSAnLi9HcmFtbWFyLmpzJztcbmltcG9ydCAqIGFzIHBleHBycyBmcm9tICcuL3BleHBycy5qcyc7XG5pbXBvcnQgKiBhcyB1dGlsIGZyb20gJy4vdXRpbC5qcyc7XG5cbi8vIExhdGUgaW5pdGlhbGl6YXRpb24gZm9yIHN0dWZmIHRoYXQgaXMgYm9vdHN0cmFwcGVkLlxuXG5pbXBvcnQgJy4vc2VtYW50aWNzRGVmZXJyZWRJbml0LmpzJzsgLy8gVE9ETzogQ2xlYW4gdGhpcyB1cC5cbkdyYW1tYXIuaW5pdEFwcGxpY2F0aW9uUGFyc2VyKG9obUdyYW1tYXIsIGJ1aWxkR3JhbW1hcik7XG5cbmNvbnN0IGlzQnVmZmVyID0gb2JqID0+XG4gICEhb2JqLmNvbnN0cnVjdG9yICYmXG4gIHR5cGVvZiBvYmouY29uc3RydWN0b3IuaXNCdWZmZXIgPT09ICdmdW5jdGlvbicgJiZcbiAgb2JqLmNvbnN0cnVjdG9yLmlzQnVmZmVyKG9iaik7XG5cbmZ1bmN0aW9uIGNvbXBpbGVBbmRMb2FkKHNvdXJjZSwgbmFtZXNwYWNlLCBidWlsZE9wdGlvbnMpIHtcbiAgY29uc3QgbSA9IG9obUdyYW1tYXIubWF0Y2goc291cmNlLCAnR3JhbW1hcnMnKTtcbiAgaWYgKG0uZmFpbGVkKCkpIHtcbiAgICB0aHJvdyBlcnJvcnMuZ3JhbW1hclN5bnRheEVycm9yKG0pO1xuICB9XG4gIHJldHVybiBidWlsZEdyYW1tYXIobSwgbmFtZXNwYWNlLCB1bmRlZmluZWQsIGJ1aWxkT3B0aW9ucyk7XG59XG5cbmV4cG9ydCBmdW5jdGlvbiBfZ3JhbW1hcihzb3VyY2UsIG9wdE5hbWVzcGFjZSwgYnVpbGRPcHRpb25zKSB7XG4gIGNvbnN0IG5zID0gX2dyYW1tYXJzKHNvdXJjZSwgb3B0TmFtZXNwYWNlLCBidWlsZE9wdGlvbnMpO1xuXG4gIC8vIEVuc3VyZSB0aGF0IHRoZSBzb3VyY2UgY29udGFpbmVkIG5vIG1vcmUgdGhhbiBvbmUgZ3JhbW1hciBkZWZpbml0aW9uLlxuICBjb25zdCBncmFtbWFyTmFtZXMgPSBPYmplY3Qua2V5cyhucyk7XG4gIGlmIChncmFtbWFyTmFtZXMubGVuZ3RoID09PSAwKSB7XG4gICAgdGhyb3cgbmV3IEVycm9yKCdNaXNzaW5nIGdyYW1tYXIgZGVmaW5pdGlvbicpO1xuICB9IGVsc2UgaWYgKGdyYW1tYXJOYW1lcy5sZW5ndGggPiAxKSB7XG4gICAgY29uc3Qgc2Vjb25kR3JhbW1hciA9IG5zW2dyYW1tYXJOYW1lc1sxXV07XG4gICAgY29uc3QgaW50ZXJ2YWwgPSBzZWNvbmRHcmFtbWFyLnNvdXJjZTtcbiAgICB0aHJvdyBuZXcgRXJyb3IoXG4gICAgICB1dGlsLmdldExpbmVBbmRDb2x1bW5NZXNzYWdlKGludGVydmFsLnNvdXJjZVN0cmluZywgaW50ZXJ2YWwuc3RhcnRJZHgpICtcbiAgICAgICAgJ0ZvdW5kIG1vcmUgdGhhbiBvbmUgZ3JhbW1hciBkZWZpbml0aW9uIC0tIHVzZSBvaG0uZ3JhbW1hcnMoKSBpbnN0ZWFkLidcbiAgICApO1xuICB9XG4gIHJldHVybiBuc1tncmFtbWFyTmFtZXNbMF1dOyAvLyBSZXR1cm4gdGhlIG9uZSBhbmQgb25seSBncmFtbWFyLlxufVxuXG5leHBvcnQgZnVuY3Rpb24gX2dyYW1tYXJzKHNvdXJjZSwgb3B0TmFtZXNwYWNlLCBidWlsZE9wdGlvbnMpIHtcbiAgY29uc3QgbnMgPSBPYmplY3QuY3JlYXRlKG9wdE5hbWVzcGFjZSB8fCB7fSk7XG4gIGlmICh0eXBlb2Ygc291cmNlICE9PSAnc3RyaW5nJykge1xuICAgIC8vIEZvciBjb252ZW5pZW5jZSwgZGV0ZWN0IE5vZGUuanMgQnVmZmVyIG9iamVjdHMgYW5kIGF1dG9tYXRpY2FsbHkgY2FsbCB0b1N0cmluZygpLlxuICAgIGlmIChpc0J1ZmZlcihzb3VyY2UpKSB7XG4gICAgICBzb3VyY2UgPSBzb3VyY2UudG9TdHJpbmcoKTtcbiAgICB9IGVsc2Uge1xuICAgICAgdGhyb3cgbmV3IFR5cGVFcnJvcihcbiAgICAgICAgJ0V4cGVjdGVkIHN0cmluZyBhcyBmaXJzdCBhcmd1bWVudCwgZ290ICcgKyBjb21tb24udW5leHBlY3RlZE9ialRvU3RyaW5nKHNvdXJjZSlcbiAgICAgICk7XG4gICAgfVxuICB9XG4gIGNvbXBpbGVBbmRMb2FkKHNvdXJjZSwgbnMsIGJ1aWxkT3B0aW9ucyk7XG4gIHJldHVybiBucztcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGdyYW1tYXIoc291cmNlLCBvcHROYW1lc3BhY2UpIHtcbiAgcmV0dXJuIF9ncmFtbWFyKHNvdXJjZSwgb3B0TmFtZXNwYWNlKTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGdyYW1tYXJzKHNvdXJjZSwgb3B0TmFtZXNwYWNlKSB7XG4gIHJldHVybiBfZ3JhbW1hcnMoc291cmNlLCBvcHROYW1lc3BhY2UpO1xufVxuXG4vLyBUaGlzIGlzIHVzZWQgYnkgb2htLWVkaXRvciB0byBpbnN0YW50aWF0ZSBncmFtbWFycyBhZnRlciBpbmNyZW1lbnRhbFxuLy8gcGFyc2luZywgd2hpY2ggaXMgbm90IG90aGVyd2lzZSBzdXBwb3J0ZWQgaW4gdGhlIHB1YmxpYyBBUEkuXG5leHBvcnQge2J1aWxkR3JhbW1hciBhcyBfYnVpbGRHcmFtbWFyfTtcblxuZXhwb3J0ICogZnJvbSAnLi9tYWluLWtlcm5lbC5qcyc7XG5leHBvcnQge0luZGVudGF0aW9uU2Vuc2l0aXZlIGFzIEV4cGVyaW1lbnRhbEluZGVudGF0aW9uU2Vuc2l0aXZlfSBmcm9tICcuL0luZGVudGF0aW9uU2Vuc2l0aXZlLmpzJztcbmV4cG9ydCB7b2htR3JhbW1hcn07XG5leHBvcnQge3BleHByc307XG5leHBvcnQge3ZlcnNpb259IGZyb20gJy4vdmVyc2lvbi5qcyc7XG4iXSwibmFtZXMiOlsiY29tbW9uLmlzU3ludGFjdGljIiwicGV4cHJzLkFwcGx5IiwiY29tbW9uLnBhZExlZnQiLCJjb21tb24uU3RyaW5nQnVmZmVyIiwiY29tbW9uLmFzc2VydCIsInV0aWwuZ2V0TGluZUFuZENvbHVtbiIsInV0aWwuZ2V0TGluZUFuZENvbHVtbk1lc3NhZ2UiLCJlcnJvcnMuaW50ZXJ2YWxTb3VyY2VzRG9udE1hdGNoIiwiY29tbW9uLmRlZmluZUxhenlQcm9wZXJ0eSIsImNvbW1vbi5yZXBlYXQiLCJwZXhwcnMuUEV4cHIiLCJwZXhwcnMuYW55IiwicGV4cHJzLmVuZCIsInBleHBycy5UZXJtaW5hbCIsInBleHBycy5SYW5nZSIsInBleHBycy5Vbmljb2RlQ2hhciIsInBleHBycy5BbHQiLCJwZXhwcnMuSXRlciIsInBleHBycy5MZXgiLCJwZXhwcnMuTG9va2FoZWFkIiwicGV4cHJzLk5vdCIsInBleHBycy5QYXJhbSIsInBleHBycy5TZXEiLCJCdWlsdEluUnVsZXMiLCJ1dGlsLmF3YWl0QnVpbHRJblJ1bGVzIiwiZXJyb3JzLnVuZGVjbGFyZWRSdWxlIiwiZXJyb3JzLmFwcGxpY2F0aW9uT2ZTeW50YWN0aWNSdWxlRnJvbUxleGljYWxDb250ZXh0IiwiZXJyb3JzLndyb25nTnVtYmVyT2ZBcmd1bWVudHMiLCJlcnJvcnMuaW5jb3JyZWN0QXJndW1lbnRUeXBlIiwiZXJyb3JzLmFwcGx5U3ludGFjdGljV2l0aExleGljYWxSdWxlQXBwbGljYXRpb24iLCJlcnJvcnMudW5uZWNlc3NhcnlFeHBlcmltZW50YWxBcHBseVN5bnRhY3RpYyIsImVycm9ycy5pbnZhbGlkUGFyYW1ldGVyIiwiZXJyb3JzLmluY29uc2lzdGVudEFyaXR5IiwicGV4cHJzLkV4dGVuZCIsImVycm9ycy5rbGVlbmVFeHBySGFzTnVsbGFibGVPcGVyYW5kIiwicGV4cHJzLk9wdCIsImNvbW1vbi5pc0xleGljYWwiLCJjb21tb24uYWJzdHJhY3QiLCJwZXhwcnMuU3BsaWNlIiwicGV4cHJzLlN0YXIiLCJwZXhwcnMuUGx1cyIsInV0aWwudW5pcXVlSWQiLCJlcnJvcnMubWlzc2luZ1NlbWFudGljQWN0aW9uIiwiY29tbW9uLnVuZXhwZWN0ZWRPYmpUb1N0cmluZyIsIm9obUdyYW1tYXIiLCJidWlsZEdyYW1tYXIiLCJlcnJvcnMud3JvbmdOdW1iZXJPZlBhcmFtZXRlcnMiLCJwZXhwcnMuQ2FzZUluc2Vuc2l0aXZlVGVybWluYWwiLCJlcnJvcnMuY2Fubm90T3ZlcnJpZGVVbmRlY2xhcmVkUnVsZSIsImR1cGxpY2F0ZVBhcmFtZXRlck5hbWVzIiwiZXJyb3JzLmR1cGxpY2F0ZVBhcmFtZXRlck5hbWVzIiwiZXJyb3JzLnRocm93RXJyb3JzIiwiZXJyb3JzLmR1cGxpY2F0ZVJ1bGVEZWNsYXJhdGlvbiIsImVycm9ycy5jYW5ub3RFeHRlbmRVbmRlY2xhcmVkUnVsZSIsImVycm9ycy5kdXBsaWNhdGVHcmFtbWFyRGVjbGFyYXRpb24iLCJlcnJvcnMudW5kZWNsYXJlZEdyYW1tYXIiLCJlcnJvcnMubXVsdGlwbGVTdXBlclNwbGljZXMiLCJjb21tb24udW5lc2NhcGVDb2RlUG9pbnQiLCJlcnJvcnMuaW52YWxpZENvZGVQb2ludCIsImVycm9ycy5ncmFtbWFyU3ludGF4RXJyb3IiXSwibWFwcGluZ3MiOiI7Ozs7OztFQUFBO0FBbUJBO0VBQ0E7RUFDQTtFQUNBO0FBQ0E7RUFDTyxTQUFTLFFBQVEsQ0FBQyxhQUFhLEVBQUU7RUFDeEMsRUFBRSxNQUFNLFVBQVUsR0FBRyxhQUFhLElBQUksRUFBRSxDQUFDO0VBQ3pDLEVBQUUsT0FBTyxZQUFZO0VBQ3JCLElBQUksTUFBTSxJQUFJLEtBQUs7RUFDbkIsTUFBTSxjQUFjO0VBQ3BCLFFBQVEsVUFBVTtFQUNsQixRQUFRLGdCQUFnQjtFQUN4QixRQUFRLHFDQUFxQztFQUM3QyxRQUFRLElBQUksQ0FBQyxXQUFXLENBQUMsSUFBSTtFQUM3QixRQUFRLEdBQUc7RUFDWCxLQUFLLENBQUM7RUFDTixHQUFHLENBQUM7RUFDSixDQUFDO0FBQ0Q7RUFDTyxTQUFTLE1BQU0sQ0FBQyxJQUFJLEVBQUUsT0FBTyxFQUFFO0VBQ3RDLEVBQUUsSUFBSSxDQUFDLElBQUksRUFBRTtFQUNiLElBQUksTUFBTSxJQUFJLEtBQUssQ0FBQyxPQUFPLElBQUksa0JBQWtCLENBQUMsQ0FBQztFQUNuRCxHQUFHO0VBQ0gsQ0FBQztBQUNEO0VBQ0E7RUFDQTtFQUNBO0VBQ08s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LFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsRUFBRSxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxhQUFhLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsU0FBUyxDQUFDLEVBQUUsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxxQkFBcUIsQ0FBQyxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxDQUFDLE1BQU0sQ0FBQyxLQUFLLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsT0FBTyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLGFBQWEsQ0FBQyxDQUFDLENBQUMsT0FBTyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsTUFBTSxDQUFDLEtBQUssQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxNQUFNLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsYUFBYSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxNQUFNLENBQUMsS0FBSyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxDQUFDLE1BQU0sQ0FBQyxLQUFLLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsT0FBTyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLGFBQWEsQ0FBQyxDQUFDLENBQUMsT0FBTyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsTUFBTSxDQUFDLEtBQUssQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxNQUFNLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsYUFBYSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxNQUFNLENBQUMsS0FBSyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDOztFQ0dqekcsT0FBTyxDQUFDLFlBQVksR0FBRyxZQUFZLENBQUM7RUFDcEMsb0JBQW9CLENBQUMsT0FBTyxDQUFDLFlBQVksQ0FBQzs7QUNKMUMsbUJBQWUsVUFBVSxDQUFDLENBQUMsU0FBUyxDQUFDLENBQUMsUUFBUSxDQUFDLCs5RkFBKzlGLENBQUMsQ0FBQyxLQUFLLENBQUMsSUFBSSxDQUFDLFVBQVUsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsQ0FBQyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsRUFBRSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEVBQUUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLFNBQVMsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsU0FBUyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxFQUFFLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxFQUFFLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsRUFBRSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxFQUFFLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsRUFBRSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsY0FBYyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEVBQUUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxFQUFFLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsRUFBRSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEVBQUUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxjQUFjLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEVBQUUsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxhQUFhLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxTQUFTLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLFdBQVcsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxlQUFlLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxTQUFTLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLGtCQUFrQixDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxhQUFhLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxTQUFTLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsYUFBYSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxlQUFlLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLGFBQWEsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLGNBQWMsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxxQkFBcUIsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxjQUFjLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxxQkFBcUIsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxrQkFBa0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxzQkFBc0IsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxrQ0FBa0MsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsQ0FBQyxzQkFBc0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLGtDQUFrQyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxjQUFjLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLFNBQVMsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsV0FBVyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsV0FBVyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsV0FBVyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxXQUFXLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsU0FBUyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsU0FBUyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxNQUFNLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLGtCQUFrQixDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsT0FBTyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsUUFBUSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxXQUFXLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsWUFBWSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsaUJBQWlCLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxpQkFBaUIsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsZUFBZSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxZQUFZLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsa0JBQWtCLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLFlBQVksQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsZUFBZSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxZQUFZLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLFdBQVcsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsb0JBQW9CLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLGVBQWUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLGVBQWUsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxNQUFNLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxNQUFNLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLFdBQVcsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxRQUFRLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsV0FBVyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLFdBQVcsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxRQUFRLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsZUFBZSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxNQUFNLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxjQUFjLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLGlCQUFpQixDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLGNBQWMsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLGNBQWMsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLFlBQVksQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxzQkFBc0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsQ0FBQyx3QkFBd0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsQ0FBQyx3QkFBd0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsQ0FBQyxzQkFBc0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsQ0FBQyxxQkFBcUIsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsQ0FBQywyQkFBMkIsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsQ0FBQyw2QkFBNkIsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsMEJBQTBCLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxzQkFBc0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsWUFBWSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxvQkFBb0IsQ0FBQyxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxzQkFBc0IsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsd0JBQXdCLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLHdCQUF3QixDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxzQkFBc0IsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMscUJBQXFCLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLDJCQUEyQixDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsNkJBQTZCLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLDBCQUEwQixDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxzQkFBc0IsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsT0FBTyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxTQUFTLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxvQkFBb0IsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsV0FBVyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxtQkFBbUIsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsU0FBUyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsb0JBQW9CLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLG1CQUFtQixDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQyxNQUFNLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsU0FBUyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxPQUFPLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsYUFBYSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsSUFBSSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLElBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsYUFBYSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENBQUMsSUFBSSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxJQUFJLENB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QUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsRUFBRSxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEVBQUUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsRUFBRSxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEVBQUUsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLFNBQVMsQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxTQUFTLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLElBQUksQ0FBQyxFQUFFLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsQ0FBQyxLQUFLLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLE1BQU0sQ0FBQyxFQUFFLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxRQUFRLENBQUMsRUFBRSxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsV0FBVyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsTUFBTSxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsVUFBVSxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLFdBQVcsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQyxDQUFDLEtBQUssQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsQ0FBQyxVQUFVLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxHQUFHLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsS0FBSyxDQUFDLENBQUMsZ0JBQWdCLENBQUMsQ0FBQyxHQUFHLENBQUMsR0FBRyxDQUFDLENBQUMsQ0FBQyxRQUFRLENBQUMsRUFBRSxDQUFDLENBQUMsQ0FBQyxDQUFDLFVBQVUsQ0FBQyxDQUFDLFFBQVEsQ0FBQyxDQUFDLGdCQUFnQixDQUFDLENBQUMsR0FBRyxDQUFDLEdBQUcsQ0FBQyxDQUFDLENBQUMsSUFBSSxDQUFDLEVBQUUs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
