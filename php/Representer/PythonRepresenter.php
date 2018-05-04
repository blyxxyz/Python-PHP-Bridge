<?php
declare(strict_types=1);

namespace blyxxyz\PythonServer\Representer;

/**
 * Build a representation that follows Python syntax.
 */
class PythonRepresenter extends Representer
{
    /** @var string */
    private $module;

    public function __construct(string $module = '')
    {
        $this->module = $module;
    }

    const TRUE = 'True';
    const FALSE = 'False';
    const NULL = 'None';

    const OBJECT_IDEN = 'PHP object';
    const RESOURCE_IDEN = 'PHP resource';

    const SEQ_ARRAY_DELIMS = ['[', ']'];
    const ASSOC_ARRAY_DELIMS = ['{', '}'];
    const KEY_SEP = ': ';
    const ITEM_SEP = ', ';

    const NAN = 'nan';
    const INF = 'inf';
    const NEG_INF = '-inf';

    // Overriding reprString would be good for correctness but a lot of work

    protected function convertClassName(string $name): string
    {
        $repr = str_replace('\\', '.', $name);
        if ($this->module !== '') {
            $repr = $this->module . '.' . $repr;
        }
        return $repr;
    }
}
