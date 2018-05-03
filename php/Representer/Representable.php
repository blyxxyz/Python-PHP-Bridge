<?php
declare(strict_types=1);

namespace blyxxyz\PythonServer\Representer;

/**
 * Classes that can provide their own representation to Representer.
 *
 * A typical implementation would either return a description that's more
 * useful than Representer's property inspection, or a way to create a
 * similar object.
 */
interface Representable
{
    /**
     * Build a representation. $callingClass::repr should be used to get
     * the representations needed to build the representation, so subclasses
     * or implementations of Representer can still use this interface.
     *
     * @param int $depth
     * @param string $callingClass
     * @return string
     */
    public function represent(
        string $callingClass = Representer::class,
        int $depth = 2
    ): string;
}
