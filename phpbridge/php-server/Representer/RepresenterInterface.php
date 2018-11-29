<?php
declare(strict_types=1);

namespace blyxxyz\PythonServer\Representer;

/**
 * Create string representations of values.
 *
 * See Representer for more information.
 */
interface RepresenterInterface
{
    public static function r($thing, int $depth = 2): string;
    public function repr($thing, int $depth = 2): string;
}
